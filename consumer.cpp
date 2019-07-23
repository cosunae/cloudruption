#include "KeyMessage.h"
#include <cstring>
#include <iostream>
#include <netcdf.h>
#include <rdkafka.h>
#include <rdkafkacpp.h>
#include <stdint.h>
#include <string>

static long msg_cnt = 0;
static int64_t msg_bytes = 0;
static int verbosity = 1;
static int partition_cnt = 0;
static bool exit_eof = false;
static int eof_cnt = 0;
static bool run = true;

void msg_consume(RdKafka::Message *message, void *opaque) {
  switch (message->err()) {
  case RdKafka::ERR__TIMED_OUT:
    break;

  case RdKafka::ERR_NO_ERROR:
    /* Real message */
    msg_cnt++;
    msg_bytes += message->len();
    if (verbosity >= 3)
      std::cerr << "Read msg at offset " << message->offset() << std::endl;
    RdKafka::MessageTimestamp ts;
    ts = message->timestamp();
    if (verbosity >= 2 &&
        ts.type != RdKafka::MessageTimestamp::MSG_TIMESTAMP_NOT_AVAILABLE) {
      std::string tsname = "?";
      if (ts.type == RdKafka::MessageTimestamp::MSG_TIMESTAMP_CREATE_TIME)
        tsname = "create time";
      else if (ts.type ==
               RdKafka::MessageTimestamp::MSG_TIMESTAMP_LOG_APPEND_TIME)
        tsname = "log append time";
      std::cout << "Timestamp: " << tsname << " " << ts.timestamp << std::endl;
    }
    if (message->key()) {
      KeyMessage *key = new KeyMessage();
      std::memcpy(key, message->key_pointer(), message->key_len());
      std::cout << "Key: " << key->myrank << ":" << key->latlen << " "
                << key->lonlen << std::endl;
    }
    if (verbosity >= 1) {
      printf("%.*s\n", static_cast<int>(message->len()),
             static_cast<const char *>(message->payload()));
    }
    break;

  case RdKafka::ERR__PARTITION_EOF:
    /* Last message */
    if (exit_eof && ++eof_cnt == partition_cnt) {
      std::cerr << "%% EOF reached for all " << partition_cnt << " partition(s)"
                << std::endl;
      run = false;
    }
    break;

  case RdKafka::ERR__UNKNOWN_TOPIC:
  case RdKafka::ERR__UNKNOWN_PARTITION:
    std::cerr << "Consume failed: " << message->errstr() << std::endl;
    run = false;
    break;

  default:
    /* Errors */
    std::cerr << "Consume failed: " << message->errstr() << std::endl;
    run = false;
  }
}

int main(int argc, char **argv) {

  std::string errstr;
  char errstrc[512];

  std::string brokers = "localhost:9092";

  /*
   * Create configuration objects
   */
  RdKafka::Conf *conf = RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL);

  /* Set bootstrap broker(s) as a comma-separated list of
   * host or host:port (default port 9092).
   * librdkafka will use the bootstrap brokers to acquire the full
   * set of brokers from the cluster. */
  if (conf->set("metadata.broker.list", brokers, errstr) !=
      RdKafka::Conf::CONF_OK) {
    fprintf(stderr, "%s\n", errstrc);
    return 1;
  }

  if (conf->set("group.id", "group1", errstr) != RdKafka::Conf::CONF_OK) {
    std::cerr << errstr << std::endl;
    exit(1);
  }

  /*
   * Create consumer using accumulated global configuration.
   */
  RdKafka::KafkaConsumer *consumer =
      RdKafka::KafkaConsumer::create(conf, errstr);
  if (!consumer) {
    std::cerr << "Failed to create consumer: " << errstr << std::endl;
    exit(1);
  }

  delete conf;

  std::cout << "% Created consumer " << consumer->name() << std::endl;

  std::vector<std::string> topics;
  topics.push_back("test3");
  /*
   * Subscribe to topics
   */
  RdKafka::ErrorCode err = consumer->subscribe(topics);
  if (err) {
    std::cerr << "Failed to subscribe to " << topics.size()
              << " topics: " << RdKafka::err2str(err) << std::endl;
    exit(1);
  }

  /*
   * Consume messages
   */
  while (run) {
    RdKafka::Message *msg = consumer->consume(1000);

    msg_consume(msg, NULL);
    delete msg;
  }
}
