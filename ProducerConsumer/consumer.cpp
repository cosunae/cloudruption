#include "Config.h"
#include "DistributedField.h"
#include "FieldProp.h"
#include "KeyMessage.h"
#include "nctools.h"
#include <cstring>
#include <filesystem>
#include <iostream>
#include <memory>
#include <netcdf.h>
#include <rdkafka.h>
#include <rdkafkacpp.h>
#include <stdint.h>
#include <string>
#include <unordered_map>

static long msg_cnt = 0;
static int64_t msg_bytes = 0;
static int verbosity = 1;
static int partition_cnt = 0;
static bool exit_eof = false;
static int eof_cnt = 0;
static bool run = true;

class MsgRepo {
  NetCDFDumper netcdfDumper_;
  std::unordered_map<std::string, std::unique_ptr<DistributedField>> msgs_;

public:
  MsgRepo(const std::vector<std::string> &topics) : netcdfDumper_(topics) {
    //    if (std::filesystem::exists(ncFilename + ".nc")) {
    //      throw std::runtime_error("Output file " + ncFilename +
    //                               ".nc can not be overwritten");
    //    }
  }
  ~MsgRepo() {}
  const std::unique_ptr<DistributedField> &
  getDistField(const KeyMessage &keyMsg) {
    if (!msgs_.count(keyMsg.key)) {
      DomainConf domain{keyMsg.totlonlen, keyMsg.totlatlen, keyMsg.levlen};
      msgs_.emplace(std::make_pair(
          keyMsg.key,
          std::make_unique<DistributedField>(std::string(keyMsg.key), domain,
                                             keyMsg.npatches * keyMsg.levlen)));
    }
    const auto &distField = msgs_.at(keyMsg.key);
    if (keyMsg.levlen != distField->levlen()) {
      throw std::runtime_error(
          "Incompatible lev len of records of the same topic");
    }
    if (keyMsg.totlatlen != distField->totlatlen()) {
      throw std::runtime_error(
          "Incompatible totlanlen len of records of the same topic");
    }
    if (keyMsg.totlonlen != distField->totlonlen()) {
      throw std::runtime_error(
          "Incompatible totlonlen len of records of the same topic");
    }

    return msgs_.at(keyMsg.key);
  }

  NetCDFDumper &getNetcdfDumper();
};

void msg_consume(RdKafka::Message *message, MsgRepo &msgRepo) {
  switch (message->err()) {
  case RdKafka::ERR__TIMED_OUT:
    break;

  case RdKafka::ERR_NO_ERROR: {
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
    if (!message->key()) {
      throw std::runtime_error("Message with no key");
    }
    KeyMessage key;
    std::memcpy(&key, message->key_pointer(), message->key_len());

    if (key.actionType_ == ActionType::HeaderData) {

      std::string topic(key.key);
      std::cout << "Received header from topic : " << topic << std::endl;
      DomainConf domain{key.totlonlen, key.totlatlen, key.levlen};

      TopicHeader *topicHeader = static_cast<TopicHeader *>(message->payload());

      std::string filename(topicHeader->filename);

      filename.replace(filename.length() - 3, 3, "C.nc");
      msgRepo.getNetcdfDumper().createFile(filename,
                                           makeDomainField(topic, domain));
    } else if (key.actionType_ == ActionType::EndData) {
      std::string topic(key.key);
      std::cout << "Received closing from topic : " << topic << std::endl;

      DomainConf domain{key.totlonlen, key.totlatlen, key.levlen};

      TopicHeader *topicHeader = static_cast<TopicHeader *>(message->payload());

      std::string filename(topicHeader->filename);

      filename.replace(filename.length() - 3, 3, "C.nc");
      msgRepo.getNetcdfDumper().closeFile(filename, topic);

    } else {
      const auto &field = msgRepo.getDistField(key);

      field->insertPatch(SinglePatch(key.ilon_start, key.jlat_start, key.lonlen,
                                     key.latlen, key.lev,
                                     static_cast<float *>(message->payload())));

      field->writeIfComplete(msgRepo.getNetcdfDumper());
    }
  } break;

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

int main() {

  std::string errstr;
  char errstrc[512];

  Config config;
  auto topics = config.getTopics();
  std::string brokers = config.getKafkaBroker();
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

  /*
   * Subscribe to topics
   */
  RdKafka::ErrorCode err = consumer->subscribe(topics);
  if (err) {
    std::cerr << "Failed to subscribe to " << topics.size()
              << " topics: " << RdKafka::err2str(err) << std::endl;
    exit(1);
  }

  MsgRepo msgRepo(topics);
  /*
   * Consume messages
   */
  while (run) {
    RdKafka::Message *msg = consumer->consume(1000);

    msg_consume(msg, msgRepo);
    delete msg;
  }
}

NetCDFDumper &MsgRepo::getNetcdfDumper() { return netcdfDumper_; }
