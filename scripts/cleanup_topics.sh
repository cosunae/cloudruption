kafkadir="/software/kafka_2.12-2.3.0"
kafkabroker="localhost:9092"
topics=`${kafkadir}/bin/kafka-topics.sh --list --bootstrap-server $kafkabroker`

for atopic in $topics; do

  echo "Deleting ... $atopic"
  ${kafkadir}/bin/kafka-topics.sh --delete --topic $atopic  --bootstrap-server $kafkabroker
done
