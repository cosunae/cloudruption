FROM ubuntu:18.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenmpi-dev git libgcc-8-dev ssh  ca-certificates \
    make g++-8 gfortran-8 tar wget \
    python3.7-dev python3-distutils libnetcdf-dev librdkafka-dev librdkafka1 librdkafka++1 \
    openssl libssl-dev curl unzip python3-pip python3-setuptools python3-dev

RUN mkdir ~/temp && cd ~/temp && \
    wget https://github.com/Kitware/CMake/releases/download/v3.16.5/cmake-3.16.5.tar.gz && \
    tar -xzvf cmake-3.16.5.tar.gz && \
    cd cmake-3.16.5/ && export CC=gcc-8 && export  CXX=g++-8 && ./bootstrap && make -j4 && make install

RUN pip3 install wheel
RUN pip3 install dash pandas squarify boto3 anytree confluent_kafka dash_treeview_antd sd_material_ui

WORKDIR /home/

RUN wget https://github.com/ecmwf/ecbuild/archive/3.1.0.tar.gz && \
    tar xvf 3.1.0.tar.gz
 
RUN wget https://github.com/ecmwf/eccodes/archive/2.12.0.tar.gz && \
    tar xvf 2.12.0.tar.gz && \
    cd eccodes-2.12.0 && mkdir build && cd build && \
    export CXX=g++-8 && export CC=gcc-8 && \
    /home/ecbuild-3.1.0/bin/ecbuild ../ -DENABLE_FORTRAN=OFF -DCMAKE_INSTALL_PREFIX=/usr/share/eccodes && \
    make -j4 install 

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install
#invalidate the cache when the head of the repo changes
ADD https://api.github.com/repos/cosunae/cloudruption/git/refs/heads/master version.json
RUN git clone https://github.com/cosunae/cloudruption.git 
RUN export eccodes_DIR=/usr/share/eccodes/lib/cmake/eccodes/ && \
    export FC=`which gortran-8` && export CXX=`which g++-8` && \
    cd /home/cloudruption/ProducerConsumer && pip3 install -v .

 
RUN mkdir /home/cloudruption/config    
RUN mkdir /data
#ADD aws/entrypoint.py /home/cloudruption/ProducerConsumer/aws/entrypoint.py
#RUN chmod +x /home/cloudruption/ProducerConsumer/aws/entrypoint.py
RUN mkdir /root/.aws/
ADD credentials /root/.aws/credentials

EXPOSE 3000
ENTRYPOINT ["/home/cloudruption/aws/producer_dash/entrypoint.py"]
#ENTRYPOINT ["/bin/bash"]
