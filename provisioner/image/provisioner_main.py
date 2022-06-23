#
# lancium-htcondor-portal/provisioner
#
# BSD license, copyright Igor Sfiligoi 2022
#
# Main entry point of the provisioner process
#

import sys
import time
import configparser

import lancium_provisioner.provisioner_lancium as provisioner_lancium
import prp_provisioner.provisioner_logging as provisioner_logging
import lancium_provisioner.provisioner_lancium_htcondor as provisioner_htcondor
import lancium_provisioner.event_loop as event_loop

def main(log_fname, max_pods_per_cluster=10, max_submit_pods_per_cluster=400, sleep_time=120):
   fconfig = configparser.ConfigParser()
   fconfig.read(('pod.conf','lancium_provisioner.conf'))
   lconfig = provisioner_lancium.ProvisionerLanciumConfig()
   cconfig = provisioner_htcondor.ProvisionerHTCConfig()

   lfconfig = fconfig['lancium'] if ('lancium' in fconfig) else fconfig['DEFAULT']
   lconfig.parse(lfconfig)
   hfconfig = fconfig['htcondor'] if ('htcondor' in fconfig) else fconfig['DEFAULT']
   cconfig.parse(hfconfig)

   log_obj = provisioner_logging.ProvisionerFileLogging(log_fname, want_log_debug=True)
   # TBD: Strong security
   schedd_whitelist=hfconfig.get('schedd_whitelist_regexp','.*')
   schedd_obj = provisioner_htcondor.ProvisionerSchedd(log_obj, {schedd_whitelist:'.*'}, cconfig)
   collector_obj = provisioner_htcondor.ProvisionerCollector(log_obj, '.*', cconfig)
   lancium_obj = provisioner_lancium.ProvisionerLancium(lconfig)

   el = event_loop.ProvisionerEventLoop(log_obj, schedd_obj, collector_obj, lancium_obj, max_pods_per_cluster, max_submit_pods_per_cluster)
   while True:
      log_obj.log_debug("[Main] Iteration started, schedd whitelist='%s'"%schedd_whitelist)
      try:
         el.one_iteration()
      except:
         log_obj.log_debug("[Main] Exception in one_iteration")
      log_obj.sync()
      time.sleep(sleep_time)

if __name__ == "__main__":
   # execute only if run as a script
   main(sys.argv[1])

