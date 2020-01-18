#Download base image ubuntu 16.04
FROM ubuntu:18.04

# Update Ubuntu Software repository
RUN apt-get update

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    g++-8 cmake libnetcdf-dev librdkafka-dev make python3

RUN apt-get update && apt-get install --yes ca-certificates curl fuse \
    && curl -L -O https://github.com/GoogleCloudPlatform/gcsfuse/releases/download/v0.27.0/gcsfuse_0.27.0_amd64.deb \
    && dpkg --install gcsfuse_0.27.0_amd64.deb \
    && mkdir /data

WORKDIR /project

COPY . /project/

RUN cd /project && \
    mkdir build && \
    cd build &&    \
    export CXX=g++-8 && \
    export CC=gcc-8 &&  \
    cmake .. -DENABLE_PRODUCER=OFF &&    \
    make -j3 

ENV PATH=$PATH:/usr/local/mpiapp
ENTRYPOINT ["python3","consumer.py","--exe","build/consumer"]
CMD ["--kafkabroker","1.1.?.?:9999"]
