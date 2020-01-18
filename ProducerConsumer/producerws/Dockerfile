#Download base image ubuntu 16.04
FROM ubuntu:18.04

# Update Ubuntu Software repository
RUN apt-get update

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    make python3 python3-pip python3-setuptools curl openssh-client

RUN pip3 install wheel connexion

WORKDIR /project

COPY . /project/

ENTRYPOINT ["./trigger_producer.py"]
CMD ["--kafkabroker","1.1.?.?:9999","--mpimaster","1.1.1.1"]
