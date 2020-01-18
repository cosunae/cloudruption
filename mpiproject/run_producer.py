import argparse
import subprocess, sys
import tempfile

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='run_producer')
    parser.add_argument('--kafkabroker', required=True, help='IP of kafka broker')
    parser.add_argument('--mpimaster', required=True, help='IP of the MPI cluster master')

    args = parser.parse_args()

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
''' % args.kafkabroker)
    bashfile.file.close()

    cmd='scp '+bashfile.name  +' '+args.mpimaster+':~/run_producer.sh'
    res= subprocess.run([cmd], shell=True, check=True)

    print("... transfer "+bashfile.name+" to mpimaster [",args.mpimaster,"]")
    if res.returncode:
        sys.exit("Problem with scp to mpimaster")

    cmd='ssh '+args.mpimaster+' bash ~/run_producer.sh'
    res= subprocess.run([cmd], shell=True, check=True)
    print("... executing run_producer.sh in mpimaster [",args.mpimaster,"]")
    if res.returncode:
        sys.exit("Problem with executing run_producer.sh in mpimaster")


