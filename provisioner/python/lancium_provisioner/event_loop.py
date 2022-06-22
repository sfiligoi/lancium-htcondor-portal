#
# lancium-htcondor-portal/provisioner
#
# BSD license, copyright Igor Sfiligoi 2022
#
# Implement the event loop
#

from . import provisioner_lancium_clustering
import provisioner_clustering

def cluster_val(x):
   xarr=x.split(';')
   xgpus=0 if len(xarr[4])==0 else int(xarr[4])
   xcpus=int(xarr[0])
   # by making GPUs more expensive than 1k cores, we guarantee that we never get a gpu job on a CPU-only node
   return xgpus*1000+xcpus


class ProvisionerEventLoop:
   def __init__(self, log_obj, schedd_obj, collector_obj, lancium_obj, max_pods_per_cluster):
      self.log_obj = log_obj
      self.schedd = schedd_obj
      self.collector = collector_obj
      self.lancium_obj = lancium_obj
      self.max_pods_per_cluster = max_pods_per_cluster
      # Hardcode for now
      self.available_clusters = {}
      for c in [16,48]:
        self.available_clusters['%i;%i;8000000;;0;;'%(c,c*2048)] = \
           ProvisionerLanciumCluster('%i;%i;8000000;;0;;'%(c,c*2048), \
           ["%i"%c, "%i"%(c*2048), '8000000', '', '0', '', ''], \
           {'PodCPUs': "%i"%c, 'PodMemory': "%i"%(c*2048), 'PodDisk': '8000000', 'PodDiskVolumes': '', 'PodGPUs': '0', 'PodGPUTypes': '', 'PodLabels': ''})
      for c in [12,48]:
        self.available_clusters['%i;%i;8000000;;%i;;'%(c,c*2048,c/3)] = \
           ProvisionerLanciumCluster('%i;%i;8000000;;%i;;'%(c,c*2048,c/3), \
           ["%i"%c, "%i"%(c*2048), '8000000', '', "%i"%(c/3), '', ''], \
           {'PodCPUs': "%i"%c, 'PodMemory': "%i"%(c*2048), 'PodDisk': '8000000', 'PodDiskVolumes': '', 'PodGPUs': "%i"%(c/3), 'PodGPUTypes': '', 'PodLabels': ''})

   def query_system(self):
      schedd_attrs = provisioner_clustering.ProvisionerClusteringAttributes().get_schedd_attributes()
      try:
         schedd_jobs = self.schedd.query_idle(projection=schedd_attrs)
         startd_pods = self.collector.query()
      except:
         self.log_obj.log_error("[ProvisionerEventQuery] Failed to query HTCondor")
         self.log_obj.sync()
         raise
      del schedd_attrs

      try:
         lancium_pods = self.lancium_obj.query()
      except:
         self.log_obj.log_error("[ProvisionerEventQuery] Failed to query lancium")
         self.log_obj.sync()
         raise

      clustering = provisioner_lancium_clustering.ProvisionerLanciumClustering()
      schedd_clusters = clustering.cluster_schedd_jobs(schedd_jobs)
      lancium_clusters = clustering.cluster_lancium_pods(lancium_pods, startd_pods)

      return (schedd_clusters, lancium_clusters)

   def one_iteration(self):
      try:
        (schedd_clusters, lancium_clusters) = self.query_system()
      except:
         self.log_obj.log_error("[ProvisionerEventLoop] Failed to query")
         self.log_obj.sync()
         return

      available_cluster_keys=list(self.available_clusters.keys())
      available_cluster_keys.sort(key=cluster_val)
      for ckey in available_cluster_keys:
         lancium_cluster = lancium_clusters[ckey] if ckey in lancium_clusters else self.available_clusters[ckey]
         schedd_cluster = None
         skeys=list(schedd_clusters.keys())
         skeys.sort(key=cluster_val)
         for skey in skeys:
            if cluster_val(skey)<=cluster_val(ckey):
               if schedd_cluster==None:
                 schedd_cluster=schedd_clusters[skey]
               else:
                 schedd_cluster.append_list(schedd_clusters[skey].elements)
               # we already processed it, we are done
               del schedd_clusters[skey]
             # ignore all others
         try:
            if schedd_cluster!=None:
               self._provision_cluster(ckey, schedd_cluster, lancium_cluster )
         except:
            self.log_obj.log_debug("[ProvisionerEventLoop] Exception in cluster '%s'"%ckey)

      self.log_obj.sync()


   # INTERNAL
   def _provision_cluster(self, cluster_id, schedd_cluster, lancium_cluster):
      "Check if we have enough lancium clusters. Submit more if needed"
      n_jobs_idle = schedd_cluster.count_idle()
      if n_jobs_idle==0:
         self.log_obj.log_debug("[ProvisionerEventLoop] Cluster '%s' n_jobs_idle==0 found!"%cluster_id)
         return # should never get in here, but just in case (nothing to do, we are done)

      # assume some latency and pod reuse
      min_pods = 1 + int(n_jobs_idle/4)
      if min_pods>20:
         # when we have a lot of jobs, slow futher
         min_pods = 20 + int((min_pods-20)/4)

      if min_pods>self.max_pods_per_cluster:
         min_pods = self.max_pods_per_cluster

      n_pods_unclaimed = lancium_cluster.count_unclaimed() if lancium_cluster!=None else 0
      self.log_obj.log_debug("[ProvisionerEventLoop] Cluster '%s' n_jobs_idle %i n_pods_unclaimed %i min_pods %i"%
                             (cluster_id, n_jobs_idle, n_pods_unclaimed, min_pods))
      if n_pods_unclaimed>=min_pods:
         pass # we have enough pods, do nothing for now
         # we may want to do some sanity checks here, eventually
      else:
         try:
            #unlike the PRP provisioner, we provision multi-job slots, so use slot attrs
            job_name = self.lancium_obj.submit(lancium_cluster.get_attr_dict(), min_pods-n_pods_unclaimed)
            self.log_obj.log_info("[ProvisionerEventLoop] Cluster '%s' Submitted %i pods as job %s"% 
                                  (cluster_id,min_pods-n_pods_unclaimed, job_name))
         except:
            self.log_obj.log_error("[ProvisionerEventLoop] Cluster '%s' Failed to submit %i pods"%
                                   (cluster_id,min_pods-n_pods_unclaimed))

      return

