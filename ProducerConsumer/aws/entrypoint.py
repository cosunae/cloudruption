#!/usr/bin/python3

import os
import os.path as path
from pathlib import Path
import json
import subprocess

if os.environ.get('aws_access_key_id') and os.environ.get('aws_secret_access_key'):
    home = str(Path.home())
    aws = home+"/.aws"

    if not path.exists(aws):
        os.mkdir(aws)
    f = open(aws+"/credentials", "w")

    f.write('[default]\n')
    f.write("aws_access_key_id = "+os.environ.get("aws_access_key_id")+"\n")
    f.write("aws_secret_access_key = " +
            os.environ.get("aws_secret_access_key") + "\n")

    f.close()

json_configfile = '/home/cloudruption/ProducerConsumer/config.json'

if os.environ.get('kafka_broker'):
    jfile = open(json_configfile, "r")
    jdata = json.load(jfile)
    jfile.close()
    jdata['kafkabroker'] = os.environ.get('kafka_broker')
    jfile = open(json_configfile, "w")
    json.dump(jdata, jfile)
    jfile.close()
os.system(
    'cd /home/cloudruption/ProducerConsumer/python && python3 producer_dash.py --producer /home/cloudruption/ProducerConsumer/build/producer --config '+json_configfile+' --pgrib /home/cloudruption/python/parseGrib.py')
