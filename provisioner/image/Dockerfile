FROM centos:centos7

# OSG RPMs
RUN yum -y install https://repo.opensciencegrid.org/osg/3.6/osg-3.6-el7-release-latest.rpm && \
    yum -y install epel-release \
                   yum-plugin-priorities && \
    yum -y install less which \
                   redhat-lsb-core && \
    yum -y install python3-pip git wget && \
    yum -y install condor python3-condor && \
    yum clean all


RUN mkdir -p /opt/lancium/bin && cd /opt/lancium/bin && wget https://portal.lancium.com/downloads/lcli && chmod a+x lcli 


# configure python packages
RUN mkdir -p /opt/prp_provisioner && cd /opt/prp_provisioner && git clone https://github.com/sfiligoi/prp-htcondor-portal.git && cd prp-htcondor-portal && git checkout main

RUN useradd provisioner && chown -R provisioner /opt/prp_provisioner

RUN su provisioner -c '/usr/bin/ln -s /opt/prp_provisioner/prp-htcondor-portal/provisioner/python/prp_provisioner /home/provisioner/prp_provisioner'

