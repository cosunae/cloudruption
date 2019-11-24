#!/bin/bash

eval `ssh-agent`
ssh-add  ~/.ssh/id_mpicluster 

ssh-keygen -f "/home/cosuna/.ssh/known_hosts" -R worker1

ssh -o "StrictHostKeyChecking no" worker1 ls

g++ mpi_c.cpp -I/usr/include/mpi -lmpi_cxx -lmpi -o mpi_c

scp mpi_c worker1:~/

mpirun -n 8 --hostfile hostfile --host master,worker1 ./mpi_c
