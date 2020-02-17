cd python
python3 toNetCDF.py --file /data/cosmo-7/laf2018020200 --topics U,V

cd ../
bash scripts/kafka_init.sh &
sleep 10

bash scripts/cleanup_topics.sh
cd ProducerConsumer
./build/producer

cd ../python

python3 toNetCDF.py  --topics U,V

