FROM rockylinux:8

# OSG RPMs
RUN yum -y install https://repo.opensciencegrid.org/osg/3.6/osg-3.6-el8-release-latest.rpm && \
    yum -y install epel-release && \
    yum -y install less which vim \
                   redhat-lsb-core && \
    yum -y install python3-pip git wget && \
    yum -y install condor python3-condor && \
    yum clean all


RUN mkdir -p /opt/lancium/bin && cd /opt/lancium/bin && wget https://portal.lancium.com/downloads/lcli && chmod a+x lcli 


# configure python packages
RUN mkdir -p /opt/prp_provisioner && cd /opt/prp_provisioner && git clone https://github.com/sfiligoi/prp-htcondor-portal.git && cd prp-htcondor-portal && git checkout main
RUN mkdir -p /opt/lancium_provisioner && cd /opt/lancium_provisioner && git clone https://github.com/sfiligoi/lancium-htcondor-portal.git && cd lancium-htcondor-portal && git checkout main

RUN useradd provisioner && chown -R provisioner /opt/prp_provisioner && chown -R provisioner /opt/lancium_provisioner

RUN su provisioner -c '/usr/bin/ln -s /opt/prp_provisioner/prp-htcondor-portal/provisioner/python/prp_provisioner /home/provisioner/prp_provisioner; /usr/bin/ln -s /opt/lancium_provisioner/lancium-htcondor-portal/provisioner/python/lancium_provisioner /home/provisioner/lancium_provisioner'

RUN su provisioner -c 'touch /home/provisioner/.bashrc; echo "export LANG=en_US.utf8" >> /home/provisioner/.bashrc'
RUN su provisioner -c 'echo "export PATH=\$PATH:/opt/lancium/bin/" >> /home/provisioner/.bashrc'
RUN su provisioner -c 'echo "export PYTHONPATH=\${PYTHONPATH}:/home/provisioner/prp_provisioner" >> /home/provisioner/.bashrc'

ADD provisioner_main.py /home/provisioner/provisioner_main.py
RUN chown provisioner /home/provisioner/provisioner_main.py

ADD setup_lancium_creds.sh /opt/provisioner/setup_lancium_creds.sh
ADD setup_htcondor_creds.sh /opt/provisioner/setup_htcondor_creds.sh
ADD provisioner_startup.sh /opt/provisioner/provisioner_startup.sh

#
# Requires env variables
# CONDOR_HOST

#
# Optional env variable
# HTCONDOR_QUERY_INSECURE
#

CMD ["/opt/provisioner/provisioner_startup.sh"]

