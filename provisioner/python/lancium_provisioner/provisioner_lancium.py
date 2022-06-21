#
# lancium-htcondor-portal/provisioner
# to be used with prp-htcondor-portal/provisioner
#
# BSD license, copyright Igor Sfiligoi@UCSD 2022
#
# Implement the Lancium interface
#

import copy
import re
import time
import subprocess

import provisioner_config_parser

ProvisionerLanciumConfigFields = ('condor_host',
                              'lancium_image',
                              'priority_class','priority_class_cpu','priority_class_gpu',
                              'labels_dict', 'envs_dict', 'pvc_volumes_dict',
                              'app_name','lancium_job_ttl',
                              'additional_requirements')

class ProvisionerLanciumConfig:
   """Config fie for ProvisionerLancium"""

   def __init__(self,
                condor_host="localhost",
                lancium_image='dummy',
                priority_class = None,
                priority_class_cpu = None,
                priority_class_gpu = None,
                base_pvc_volumes = {},
                additional_labels = {},
                additional_envs = {},
                additional_volumes = {},
                app_name = 'lancium-wn',
                lancium_job_ttl = 24*3600, # clean after 1 day
                additional_requirements = ""):
      """
      Arguments:
         condor_host: string (Optional)
             DNS address of the HTCOndor collector
         lancium_image: string (Optional)
             WN Container image to use in the pod
         priority_class: string (Optional)
             priorityClassName to associate with the pod
         priority_class_cpu: string (Optional)
             priorityClassName to associate with CPU pod
         priority_class_cpu: string (Optional)
             priorityClassName to associate with GPU pod
         base_pvc_volumes: list of strings (Optional)
             PersistentVolumeClaims to add to the container, vvalues is mountpoint
         additional_labels: dictionary of strings (Optional)
             Labels to attach to the pod
         additional_envs: dictionary of strings (Optional)
             Environment values to add to the container
         additional_volumes: dictionary of (volume,mount) pairs (Optional)
             Volumes to mount in the pod. Both volume and mount must be a dictionary.
      """
      self.condor_host = copy.deepcopy(condor_host)
      self.lancium_image = copy.deepcopy(lancium_image)
      self.priority_class = copy.deepcopy(priority_class)
      self.priority_class_cpu = copy.deepcopy(priority_class_cpu)
      self.priority_class_gpu = copy.deepcopy(priority_class_gpu)
      self.base_pvc_volumes = copy.deepcopy(base_pvc_volumes)
      self.additional_labels = copy.deepcopy(additional_labels)
      self.additional_envs = copy.deepcopy(additional_envs)
      self.additional_volumes = copy.deepcopy(additional_volumes)
      self.app_name = copy.deepcopy(app_name)
      self.lancium_job_ttl = lancium_job_ttl
      self.additional_requirements = copy.deepcopy(additional_requirements)

   def parse(self,
             dict,
             fields=ProvisionerLanciumConfigFields):
      """Parse the valuies from a dictionary"""
      self.condor_host = provisioner_config_parser.update_parse(self.condor_host, 'condor_host', 'str', fields, dict)
      self.lancium_image = provisioner_config_parser.update_parse(self.lancium_image, 'lancium_image', 'str', fields, dict)
      self.priority_class = provisioner_config_parser.update_parse(self.priority_class, 'priority_class', 'str', fields, dict)
      self.priority_class_cpu = provisioner_config_parser.update_parse(self.priority_class_cpu, 'priority_class_cpu', 'str', fields, dict)
      self.priority_class_gpu = provisioner_config_parser.update_parse(self.priority_class_gpu, 'priority_class_gpu', 'str', fields, dict)
      self.base_pvc_volumes = provisioner_config_parser.update_parse(self.base_pvc_volumes, 'pvc_volumes_dict', 'dict', fields, dict)
      self.additional_labels = provisioner_config_parser.update_parse(self.additional_labels, 'labels_dict', 'dict', fields, dict)
      self.additional_envs = provisioner_config_parser.update_parse(self.additional_envs, 'envs_dict', 'dict', fields, dict)
      self.app_name = provisioner_config_parser.update_parse(self.app_name, 'app_name', 'str', fields, dict)
      self.lancium_job_ttl = provisioner_config_parser.update_parse(self.lancium_job_ttl, 'lancium_job_ttl', 'int', fields, dict)
      self.additional_requirements = provisioner_config_parser.update_parse(self.additional_requirements, 'additional_requirements', 'str', fields, dict)

class ProvisionerLancium:
   """Kubernetes Query interface"""

   def __init__(self, config):
      self.start_time = int(time.time())
      self.submitted = 0
      # TODO: Put it into the config
      self.image_startup_script="/usr/local/sbin/supervisord_startup.sh"
      # use deepcopy to avoid surprising changes at runtime
      self.app_name = copy.deepcopy(config.app_name)
      self.lancium_job_ttl = config.lancium_job_ttl
      self.condor_host = copy.deepcopy(config.condor_host)
      self.lancium_image = copy.deepcopy(config.lancium_image)
      self.priority_class = copy.deepcopy(config.priority_class)
      self.priority_class_cpu = copy.deepcopy(config.priority_class_cpu)
      self.priority_class_gpu = copy.deepcopy(config.priority_class_gpu)
      self.base_pvc_volumes = copy.deepcopy(config.base_pvc_volumes)
      self.additional_labels = copy.deepcopy(config.additional_labels)
      self.additional_envs = copy.deepcopy(config.additional_envs)
      self.additional_volumes = copy.deepcopy(config.additional_volumes)
      self.additional_requirements = copy.deepcopy(config.additional_requirements)
      return

   def query(self):
      """Return the list of jobs"""

      pods=[]

      process = subprocess.Popen(['lcli','job','show', '-f', 'csv'],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      stdout, stderr = process.communicate()
      if process.returncode!=0:
        raise OSError("Failed to query Lancium jobs")

      idxs={}
      isfirst=True
      for rline in stdout.splitlines():
        line=rline.decode()
        larr=line.strip().split(",")
        if len(larr)!=3:
           continue # should never get in here, but just in case

        if isfirst:
          isfirst=False
          for i in range(3):
            idxs[larr[i]]=i
          continue # just build the idxs

        label_str=larr[idxs['name']]
        if label_str.startswith('lancium-app:%s lancium-job:'%self.app_name):
          larr=line.strip().split(",")
          if len(larr)!=3:
            continue # should never get in here, but just in case
          pod_id=larr[idxs['id']]
          pod_status=larr[idxs['status']]
          label_list=label_str.split()
          podattrs={'lancium-id':pod_id, 'Status':pod_status}
          for el in label_list:
             elarr=el.split(":",1)
             if len(elarr)!=2:
               continue #ignore malformed entries
             podattrs[elarr[0]]=elarr[1]
          podattrs['Name']=podattrs['lancium-job']
          pods.append(podattrs)

      return pods

   def submit_one(self, attrs):
      # first ensure that the basic int values are valid
      int_vals={}
      for k in ('CPUs','GPUs','Memory','Disk'):
         int_vals[k] = int(attrs[k])

      job_name = '%s-%x-%06x'%(self.app_name,self.start_time,self.submitted)
      self.submitted = self.submitted + 1

      labels = [
                 'lancium-app:%s'%self.app_name,
                 'lancium-job:%s'%job_name,
                 'prp-htcondor-portal:%s'%'wn',
                 'PodCPUs:%i'%int_vals['CPUs'],
                 'PodGPUs:%i'%int_vals['GPUs'],
                 'PodMemory:%i'%int_vals['Memory'],
                 'PodDisk:%i'%int_vals['Disk']
               ]
      # TODO: Handle any optional labels
      #for k in self.additional_labels.keys():
      #   labels[k] = copy.copy(self.additional_labels[k])
      #self._augment_labels(labels, attrs)

      label_str=" ".join(labels)

      req = {
               'mem':   '%i'%int((int_vals['Memory']+1023)/1024),
               'cores': '%i'%int(int_vals['CPUs'])
            }
      if int(int_vals['GPUs'])>0:
         req['gpu-count'] = '%i'%int(int_vals['GPUs'])
         req['gpu'] = 'k80'

      #TODO: Request Ephemeral storage
      env_list = [ ('LANCIUM_PROVISIONER_TYPE', 'PRPHTCondorProvisioner'),
                   ('LANCIUM_PROVISIONER_NAME', self.app_name),
                   ('LANCIUM_JOB_NAME', job_name),
                   ('CONDOR_HOST', self.condor_host),
                   ('STARTD_NOCLAIM_SHUTDOWN', '1200'),
                   ('NUM_CPUS', "%i"%int_vals['CPUs']),
                   ('NUM_GPUS', "%i"%int_vals['GPUs']),
                   ('MEMORY', "%i"%int_vals['Memory']),
                   ('DISK',   "%i"%int_vals['Disk'])]

      if self.additional_requirements != "" :
         env_list.append(('ADDITIONAL_REQUIREMENTS',self.additional_requirements))

      for k in self.additional_envs:
         env_list.append((k,self.additional_envs[k]))
      self._augment_environment(env_list, attrs)

      # lancium needs env as spaced string after cmdline
      cmd_slist = [self.image_startup_script]
      for el in env_list:
         cmd_slist.append(el[0])
         cmd_slist.append(el[1])
      cmd_str=" ".join(cmd_slist)

      # no other defaults, so just start with the additional ones
      volumes_raw = copy.deepcopy(self.additional_volumes)
      self._augment_volumes(volumes_raw, attrs)
      volumes_list=list(volumes_raw.values())

      priority_class = self._get_priority_class(attrs)
      # TODO: use priority_class

      # create the cmdline string (as a list first)
      sh_slist=["lcli", "job", "run",\
                "--name", label_str,\
                "--command", cmd_str,\
                "--image", self.lancium_image]
      for el in volumes_raw.values():
        sh_slist.append("--input-file")
        sh_slist.append(el)
      for k in req.keys():
        el=req[k]
        sh_slist.append("--%s"%k)
        sh_slist.append(el)

      process = subprocess.Popen(sh_slist,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      stdout, stderr = process.communicate()
      if process.returncode!=0:
        raise OSError("Failed to launch Lancium job: %s"%stderr.decode())
      # TODO: Better error handling

      return "launched"

   def submit(self, attrs, n_pods=1):
      for i in range(n_pods):
        self.submit_one(attrs)
      return "launched_%i"%n_pods

   # INTERNAL

   # These can be re-implemented by derivative classes
   def _get_lancium_image(self, attrs):
      return (self.lancium_image,self.lancium_image_pull_policy)

   def _get_priority_class(self, attrs):
      if int(attrs['GPUs'])>0:
         pc = self.priority_class_gpu
      else:
         pc = self.priority_class_cpu
      if pc==None:
         pc = self.priority_class
      return pc

   def _augment_labels(self, labels, attrs):
      """Add any additional labels to the dictionary (attrs is read-only)"""
      return

   def _augment_environment(self, env_list, attrs):
      """Add any additional (name,value) pairs to the list (attrs is read-only)"""
      return

   def _augment_volumes(self, volumes, attrs):
      """Add any additional (volume,mount) pair to the dictionary (attrs is read-only)"""

      for v in self.base_pvc_volumes:
         volumes[v] = self.base_pvc_volumes[v]

      # by default, we mount the token secret
      volumes['configpasswd'] = 'prp-wn.token'

      return

