#!/bin/bash
su provisioner -c "touch /home/provisioner/.bashrc"

su provisioner -c "echo \"export LANCIUM_API_KEY=`cat /etc/lancium/tokens.d/lancium_key.bin`\" >> /home/provisioner/.bashrc"

