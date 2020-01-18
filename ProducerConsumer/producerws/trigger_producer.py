#!/usr/bin/env python3

import connexion
import data
import argparse
import subprocess, sys
import tempfile

#kafkabroker="K"
#mpimaster="L"

def trigger():
    bashfile = tempfile.NamedTemporaryFile('w')

    bashfile.write('''\
rm -rf gcloudcomm
git clone https://github.com/cosunae/gcloudcomm.git
cd gcloudcomm/ProducerConsumer/

sed  's/localhost:9092/%s/g' config.json -i

mkdir build
cd build

export CXX=g++-8
cmake ../
make -j3

cd ..
./build/producer
''' % data.kafkabroker)
    bashfile.file.close()

    cmd='scp '+bashfile.name  +' '+data.mpimaster+':~/run_producer.sh'
    res= subprocess.run([cmd], shell=True, check=True, timeout=5)

    print("... transfer "+bashfile.name+" to mpimaster [",data.mpimaster,"]")
    if res.returncode:
        sys.exit("Problem with scp to mpimaster")

    cmd='ssh '+data.mpimaster+' bash ~/run_producer.sh'
    res= subprocess.run([cmd], shell=True, check=True, timeout=5)
    print("... executing run_producer.sh in mpimaster [",data.mpimaster,"]")
    if res.returncode:
        sys.exit("Problem with executing run_producer.sh in mpimaster")



def post_greeting(name: str) -> str:
    trigger()
    return 'Hello {name}'.format(name=name)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='run_producer')
    parser.add_argument('--kafkabroker', required=True, help='IP of kafka broker')
    parser.add_argument('--mpimaster', required=True, help='IP of the MPI cluster master')

    args = parser.parse_args()

    data.kafkabroker=args.kafkabroker
    data.mpimaster=args.mpimaster

    app = connexion.FlaskApp(__name__, port=9090, specification_dir='swagger/')
    app.add_api('producer-api.yaml', arguments={'title': 'Hello World Example'})
    app.run()
