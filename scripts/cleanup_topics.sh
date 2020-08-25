kafkadir="/software/kafka_2.12-2.6.0"
kafkabroker="b-2.cosmo-kafka.hifwlq.c4.kafka.eu-central-1.amazonaws.com:9092,b-1.cosmo-kafka.hifwlq.c4.kafka.eu-central-1.amazonaws.com:9092,b-3.cosmo-kafka.hifwlq.c4.kafka.eu-central-1.amazonaws.com:9092"
topics=`${kafkadir}/bin/kafka-topics.sh --list --bootstrap-server $kafkabroker`

for atopic in $topics; do

  echo "Deleting ... $atopic"
  ${kafkadir}/bin/kafka-topics.sh --delete --topic $atopic  --bootstrap-server $kafkabroker
done
