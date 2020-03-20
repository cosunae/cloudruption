## Run docker container

The docker_env should contain aws_access_key_id, aws_secret_access_key if required for aws authentication and a kafka_broker
docker run -v /code/cloudruption/ProducerConsumer/:/home/cloudruption/config --env-file=docker_env --network="host" a7582eb84a86


## Tag and push an image

docker tag a7582eb84a86 066650776666.dkr.ecr.eu-central-1.amazonaws.com/cloudruption-repo:v1.0
docker -vv push 066650776666.dkr.ecr.eu-central-1.amazonaws.com/cloudruption-repo:v1.0
