#!/bin/bash

gcloud compute instances create master worker1 --source-snapshot=mpi-cluster-ubuntu --machine-type=n1-standard-4  --zone=europe-west6-a
sleep 10
ip1=`gcloud compute instances describe master --format='get(networkInterfaces[0].accessConfigs[0].natIP)'`
ip2=`gcloud compute instances describe worker1 --format='get(networkInterfaces[0].accessConfigs[0].natIP)'`

ssh-keygen -f "/home/cosuna/.ssh/known_hosts" -R $ip1
ssh-keygen -f "/home/cosuna/.ssh/known_hosts" -R $ip2
ssh-keygen -f "/home/cosuna/.ssh/known_hosts" -R worker1
ssh-keygen -f "/home/cosuna/.ssh/known_hosts" -R master

echo "Setup ssh cluster"
ssh-keygen -t rsa -f id_mpicluster -N ""
ssh-copy-id -i id_mpicluster $ip2 -o "StrictHostKeyChecking no"
ssh-copy-id -i id_mpicluster $ip1 -o "StrictHostKeyChecking no"

scp id_mpicluster $ip1:~/.ssh/

echo "Execute mpi setup" 
scp setup_mpi_cluster.sh $ip1:~/
ssh $ip1 gcsfuse ecmwf_data /data
ssh $ip2 gcsfuse ecmwf_data /data

echo "Creating a hostfile"
echo "-------------------"
echo "localhost slots=4" > hostfile
echo "worker1 slots=4" >> hostfile

scp hostfile $ip1:~/

echo "localhost slots=4" > hostfile
echo "master slots=4" >> hostfile

scp hostfile $ip2:~/

echo "Copying source code" 
scp mpi_c.cpp Dockerfile $ip1:~/

ssh $ip1 bash ~/setup_mpi_cluster.sh
