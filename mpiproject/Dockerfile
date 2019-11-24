#Download base image ubuntu 16.04
FROM ubuntu:16.04

# Update Ubuntu Software repository
RUN apt-get update

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libopenmpi-dev g++ && \
    mkdir /usr/local/mpiapp && chown 666 /usr/local/mpiapp

USER 666

COPY mpi_c.cpp /usr/local/mpiapp

RUN cd /usr/local/mpiapp/ && \
    g++ mpi_c.cpp -I/usr/include/mpi -lmpi_cxx -lmpi -o mpi_c

ENV PATH=$PATH:/usr/local/mpiapp

