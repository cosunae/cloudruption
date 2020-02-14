topics=`/software/kafka_2.12-2.3.0/bin/kafka-topics.sh --list --bootstrap-server localhost:9092`

for atopic in $topics; do

  echo "Deleting ... $atopic"
  /software/kafka_2.12-2.3.0/bin/kafka-topics.sh --delete --topic $atopic  --bootstrap-server localhost:9092
done
