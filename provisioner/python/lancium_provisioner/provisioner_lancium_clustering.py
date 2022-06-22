#
# lancium-htcondor-portal/provisioner
# to be used with prp-htcondor-portal/provisioner
#
# BSD license, copyright Igor Sfiligoi 2022
#
# Implement the clusterinng
#

from provisioner_clustering import ProvisionerCluster,ProvisionerClustering

class ProvisionerLanciumCluster(ProvisionerCluster):
   def __init__(self, key, attr_vals, pod_attrs):
      ProvisionerCluster.__init__(self, key, attr_vals)
      self.pod_attrs = pod_attrs

   def count_states(self):
      "Returns (unclaimed,claimed,failed,unknown) counts"
      unclaimed_cnt = 0
      claimed_cnt = 0
      failed_cnt = 0
      unknown_cnt = 0

      for el in self.elements:
         pod_el = el[0]
         status="%s"%pod_el['Status']
         if status=="running":
            startd_els = el[1]
            if startd_els!=None:
              state = "Unclaimed"
              for el in startd_els:
                elstate = "%s"%startd_el['State']
                if elstate=="Claimed":
                  # a single claimed is good enough
                  state=elstate
                  break
            else:
              state = "None"
            # we will count all Running pods that are not yet claimed
            if state!="Claimed":
              unclaimed_cnt+=1
            else:
              claimed_cnt+=1
         elif status in ("submitted","queued","created"):
            # we can assume these are unclaimed at all times
            unclaimed_cnt+=1
         elif status in ["finished","delete pending"]:
            # we can safely ignore these
            pass
         elif status=="error":
            failed_cnt+=1
         else:
            unknown_cnt+=1
      return (unclaimed_cnt,claimed_cnt,failed_cnt,unknown_cnt)

   def count_unclaimed(self):
      return self.count_states()[0]

class ProvisionerLanciumClustering(ProvisionerClustering):
   def __init__(self):
      ProvisionerClustering.__init__(self)

   def cluster_lancium_pods(self, lancium_pods, startd_ads):
      startd_dict={}
      # dict of lists, since we use partitionable slots
      for ad in startd_ads:
         k=ad["LanciumJobName"]
         if k in startd_dict.keys():
           startd_dict[k].append(ad)
         else:
           startd_dict[k]=[ad]
         del k

      clusters={}
      for pod in lancium_pods:
         if pod['Name'] in startd_dict:
           pod_ads = startd_dict[pod['Name'] ]
         else:
           pod_ads = None
         pod_attrs=[]
         key_attrs={}
         for k in self.attrs.attributes.keys():
            # We can reuse the k8s variant, uses the same logic
            podk = self.attrs.expand_k8s_attr(k)
            if podk in pod.keys():
               val = pod[podk]
            else:
               val = self.attrs.attributes[k]
            pod_attrs.append("%s"%val)
            key_attrs[podk]=val
         pod_key=";".join(pod_attrs)
         if pod_key not in clusters:
            clusters[pod_key] = ProvisionerLanciumCluster(pod_key, pod_attrs, key_attrs)
         clusters[pod_key].append( (pod,pod_ads) )
         # cleanup to avoid accidental reuse
         del pod_attrs
         del key_attrs
         del pod_ads

      return clusters

