FROM ubuntu:18.04

RUN apt-get update && apt-get install -y --no-install-recommends \
   libopenmpi-dev git libgcc-8-dev ssh  ca-certificates 

RUN apt-get update && apt-get install -y --no-install-recommends make g++-8 tar wget \
    python3.7-dev python3-distutils libnetcdf-dev librdkafka-dev librdkafka1 librdkafka++1 \
    openssl libssl-dev

RUN apt-get purge cmake
RUN mkdir ~/temp && cd ~/temp && \
    wget https://github.com/Kitware/CMake/releases/download/v3.16.5/cmake-3.16.5.tar.gz && \
    tar -xzvf cmake-3.16.5.tar.gz && \
    cd cmake-3.16.5/ && export CC=gcc-8 && export  CXX=g++-8 && ./bootstrap && make -j4 && make install

WORKDIR /home/

RUN wget https://github.com/ecmwf/ecbuild/archive/3.1.0.tar.gz && \
    tar xvf 3.1.0.tar.gz
 
RUN wget https://github.com/ecmwf/eccodes/archive/2.12.0.tar.gz && \
    tar xvf 2.12.0.tar.gz && \
    cd eccodes-2.12.0 && mkdir build && cd build && \
    export CXX=g++-8 && export CC=gcc-8 && \
    /home/ecbuild-3.1.0/bin/ecbuild ../ -DENABLE_FORTRAN=OFF -DCMAKE_INSTALL_PREFIX=/usr/share/eccodes && \
    make -j4 install 

RUN git clone https://github.com/cosunae/cloudruption.git && \
     cd  cloudruption/ProducerConsumer && export CXX=g++-8 && export CC=gcc-8 && \
     mkdir build  && cd build &&  cmake  -DENABLE_PRODUCER=ON -Deccodes_DIR=/usr/share/eccodes/lib/cmake/eccodes/ .. && \
    make -j3 
RUN mkdir /home/cloudruption/config    
RUN mkdir /cdata
RUN chmod +x /home/cloudruption/ProducerConsumer/aws/entrypoint.sh
ENTRYPOINT ["/home/cloudruption/ProducerConsumer/aws/entrypoint.sh"]
