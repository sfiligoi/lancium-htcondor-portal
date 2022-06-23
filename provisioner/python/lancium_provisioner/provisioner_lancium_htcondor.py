#
# lancium-htcondor-portal/provisioner
#
# BSD license, copyright Igor Sfiligoi 2022
#
# Implement the htcondor interface
#

import copy
import re
import htcondor
import classad

import provisioner_config_parser

ProvisionerHTCConfigFields = ('condor_host',
                              'app_name',
                              'additional_requirements')

class ProvisionerHTCConfig:
   """Config file for HTCOndor provisioning classes"""

   def __init__(self, 
                condor_host="cm-1.ospool.osg-htc.org",
                app_name = 'lancium-wn',
                additional_requirements = ""):
      self.condor_host = copy.deepcopy(condor_host)
      self.app_name = copy.deepcopy(app_name)
      self.additional_requirements = copy.deepcopy(additional_requirements)

   def parse(self,
             dict,
             fields=ProvisionerHTCConfigFields):
      """Parse the valuies from a dictionary"""
      self.condor_host = provisioner_config_parser.update_parse(self.condor_host, 'condor_host', 'str', fields, dict)
      self.app_name = provisioner_config_parser.update_parse(self.app_name, 'app_name', 'str', fields, dict)
      self.additional_requirements = provisioner_config_parser.update_parse(self.additional_requirements, 'additional_requirements', 'str', fields, dict)

class ProvisionerSchedd:
   """HTCondor schedd interface"""

   def __init__(self, log_obj, trusted_schedds, config):
      """
      Arguments:
         log_obj: object
             Logging object
         trusted_schedds: dictionary, NameRegexp:AuthenticatedIdentityRegexp
             Set of schedds to query. Both name and AuthenticatedIdentity are regexp.
      """
      self.log_obj = log_obj
      self.trusted_schedds = copy.deepcopy(trusted_schedds)
      self.additional_requirements = copy.deepcopy(config.additional_requirements)

   def query_idle(self, projection=[]):
      """Return the list of idle jobs for my provisioner"""
      return self.query(job_status=1, projection=projection)


   def query(self, job_status, projection=[]):
      """Return the list of jobs for my provisioner"""

      full_projection=['ClusterId','ProcId','JobStatus']+projection
      query_str='(JobStatus=?=%i)'%job_status
      if self.additional_requirements != "":
         query_str += ' && (%s)'%self.additional_requirements

      jobs=[]

      sobjs=self._get_schedd_objs()
      for sclassad in sobjs:
         s=htcondor.Schedd(sclassad)
         sname=sclassad['Name']
         try:
            myjobs=s.xquery(query_str, full_projection)
         except:
            self.log_obj.log_debug("[ProvisionerSchedd] Failed to query HTCondor schedd '%s'"%sname)
            raise

         self._append_jobs(sname, jobs, myjobs)

      return jobs


   # INTERNAL
   def _append_jobs(self, schedd_name, jobs, myjobs):
      """jobs is a list and will be updated in-place"""
      minvals={'RequestMemory':4096,'RequestDisk':8000000}
      for job in myjobs:
         jobattrs={'ScheddName':schedd_name}
         for k in job.keys():
            if k in minvals.keys():
               # the default RequestMemory and RequestDisk in condor is dynamic
               # and the initial value (after eval) is way too low
               # Treat very low values as undefines
               val = int(job.eval(k))
               if val>=minvals[k]:
                  jobattrs[k]="%s"%val
               #else pretend it is not there
            else:
               # convert all values to strings, for easier management
               # also expand all expresstions
               jobattrs[k]="%s"%job.eval(k)
         jobs.append(jobattrs)
      return

   def _get_schedd_objs(self):
      sobjs=[]
      c = htcondor.Collector()
      try:
         slist=c.query(ad_type=htcondor.AdTypes.Schedd,projection=['Name','AuthenticatedIdentity','MyAddress','AddressV1','Machine'])
      except:
         self.log_obj.log_debug("[ProvisionerSchedd] Failed to retrieve HTCondor schedd list")
         raise

      for s in slist:
         try:
            smachine=s['Machine']
            sname=s['Name']
            sauthid=s['AuthenticatedIdentity']
         except:
            # if I cannot find all, it is invalid
            continue
         if not self._is_valid_schedd(sname,sauthid):
            continue # ignore untrusted schedds
         sobjs.append(s)
         # cleaup to avoid accidental reuse
         del smachine
         del sname
         del sauthid
      return sobjs

   def _is_valid_schedd(self, schedd_name, schedd_authid):
      found = False
      for nameregex in self.trusted_schedds.keys():
         if re.fullmatch(nameregex,schedd_name):
            # found a valid schedd name
            authregex=self.trusted_schedds[nameregex]
            if re.fullmatch(authregex,schedd_authid):
               #it also matches the identity
               found = True
               break # found, we are done
         # ignore all others
      return found


class ProvisionerCollector:
   """HTCondor Collector/startd interface"""

   def __init__(self, log_obj, startd_identity, config):
      """
      Arguments:
         log_obj: object
             Logging object
         startd_identity: string
             AuthenticatedIdentity Regexp used as a whitelist
      """
      self.log_obj = log_obj
      self.startd_identity = copy.deepcopy(startd_identity)
      self.app_name = copy.deepcopy(config.app_name)

   def query(self,  projection=[]):
      """Return the list of startds for my provisioner"""

      full_projection=['Machine','Name','AuthenticatedIdentity','State','Activity','LanciumProvisionerType', 'LanciumProvisionerName', 'LanciumJobName']+projection
      startds=[]

      c = htcondor.Collector()
      try:
         slist=c.query(ad_type=htcondor.AdTypes.Startd,projection=full_projection,
                       constraint='(LanciumProvisionerType=?="PRPHTCondorProvisioner")&&(LanciumProvisionerName=?="%s")'%self.app_name)
      except:
         self.log_obj.log_debug("[ProvisionerCollector] Failed to retrieve HTCondor startd list")
         raise

      for s in slist:
         try:
            smachine=s['Machine']
            sname=s['Name']
            sauthid=s['AuthenticatedIdentity']
         except:
            # if I cannot find all, it is invalid
            continue
         if not re.fullmatch(self.startd_identity,sauthid):
            # not trusted, ignore
            continue
         adattrs={}
         for k in s.keys():
            # convert all values to strings, for easier management
            # also eval any expressions
            adattrs[k]="%s"%s.eval(k)
         startds.append(adattrs)
         # cleaup to avoid accidental reuse
         del smachine
         del sname
         del sauthid

      return startds

