#!/bin/bash

# basic setup
/opt/provisioner/setup_lancium_creds.sh
/opt/provisioner/setup_htcondor_creds.sh

mkdir -p /var/log/provisioner/logs
chown provisioner:provisioner /var/log/provisioner/logs

if [ "x${CONDOR_HOST}" == "x" ]; then
  echo "Missing CONDOR_HOST"
  sleep 15
  exit 1
fi

echo "CONDOR_HOST=${CONDOR_HOST}" > /etc/condor/config.d/02_condor_host.config

echo "[DEFAULT]" > /home/provisioner/pod.conf
echo "condor_host=${CONDOR_HOST}" >> /home/provisioner/pod.conf

trap 'echo signal received!; kill $(jobs -p); wait' SIGINT SIGTERM

echo "`date` Starting provisioner_main.py"
su -l provisioner -c "cd /home/provisioner && python3 provisioner_main.py /var/log/provisioner/logs/provisioner.log" &
wait
rc=$?
echo "`date` End of provisioner_main.py, rc=${rc}"

