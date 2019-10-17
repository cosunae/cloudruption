#include "Config.h"
#include "Field.h"
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

class SinglePatch {
public:
  SinglePatch(size_t ilonstart, size_t jlatstart, size_t lonlen, size_t latlen,
              size_t lev, float *data)
      : ilonstart_(ilonstart), jlatstart_(jlatstart), lonlen_(lonlen),
        latlen_(latlen), lev_(lev) {
    data_ = static_cast<float *>(malloc(lonlen * latlen * sizeof(float)));
    memcpy(data_, data, lonlen * latlen * sizeof(float));
  }
  // TODO fix this
  //  ~SinglePatch() { free(data_); }

  size_t ilonStart() { return ilonstart_; }
  size_t jlatStart() { return jlatstart_; }
  size_t lonlen() { return lonlen_; }
  size_t latlen() { return latlen_; }
  size_t lev() { return lev_; }
  float operator()(int i, int j) { return data_[j * lonlen_ + i]; }

private:
  size_t ilonstart_, jlatstart_;
  size_t lonlen_, latlen_, lev_;

  float *data_;
};

class DistributedField {
  std::string fieldName_;

  DomainConf domain_;
  size_t npatches_;
  std::vector<SinglePatch> patches_;

public:
  DistributedField(std::string fieldName, const DomainConf &domainConf,
                   size_t npatches)
      : fieldName_(fieldName), domain_(domainConf), npatches_(npatches) {}

  void insertPatch(size_t ilonstart, size_t jlatstart, size_t lonlen,
                   size_t latlen, size_t k, float *data) {
    patches_.push_back(
        std::move(SinglePatch{ilonstart, jlatstart, lonlen, latlen, k, data}));
  }
  void writeIfComplete(NetCDFDumper &netcdfDumper) {
    if (npatches_ != patches_.size())
      return;

    std::vector<float> fullfield(totlonlen() * totlatlen() * levlen());

    for (auto &patch : patches_) {
      for (int j = 0; j < patch.latlen(); ++j) {
        for (int i = 0; i < patch.lonlen(); ++i) {
          fullfield[patch.lev() * totlonlen() * totlatlen() +
                    (j + patch.jlatStart()) * totlonlen() +
                    (i + patch.ilonStart())] = patch(i, j);
        }
        //            }
        //          }
        //          nextilon += patch.lonlen();
        //          if (nextilon == totlonlen_) {
        //            nextjlat += patch.latlen();
        //            if (nextjlat != totlatlen_)
        //              nextilon = 0;
        //          }
        //          continue;
      }
    }
    netcdfDumper.writeVar(fieldName_, fullfield.data());

    patches_.clear();
  }

  size_t levlen() const;
  size_t totlonlen() const;
  size_t totlatlen() const;
};

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
      DomainConf domain{0, 0, keyMsg.totlonlen, keyMsg.totlatlen, keyMsg.levlen,
                        0, 0};
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

    if (key.actionType_ == ActionType::InitFile) {

      std::string topic(key.key);
      std::cout << "Received header from topic : " << topic << std::endl;
      DomainConf domain{0, 0, key.totlonlen, key.totlatlen, key.levlen, 0, 0};

      TopicHeader *topicHeader = static_cast<TopicHeader *>(message->payload());

      std::string filename(topicHeader->filename);

      filename.replace(filename.length() - 3, 3, "C.nc");
      msgRepo.getNetcdfDumper().createFile(filename,
                                           makeDomainField(topic, domain));
    } else if (key.actionType_ == ActionType::CloseFile) {
      std::string topic(key.key);
      std::cout << "Received closing from topic : " << topic << std::endl;

      DomainConf domain{0, 0, key.totlonlen, key.totlatlen, key.levlen, 0, 0};

      TopicHeader *topicHeader = static_cast<TopicHeader *>(message->payload());

      std::string filename(topicHeader->filename);

      filename.replace(filename.length() - 3, 3, "C.nc");
      msgRepo.getNetcdfDumper().closeFile(filename, topic);

    } else {
      const auto &field = msgRepo.getDistField(key);
      field->insertPatch(key.ilon_start, key.jlat_start, key.lonlen, key.latlen,
                         key.lev, static_cast<float *>(message->payload()));

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

  std::string brokers = "localhost:9092";

  Config config;
  auto topics = config.getTopics();

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

size_t DistributedField::levlen() const { return domain_.levels; }

size_t DistributedField::totlonlen() const { return domain_.isize; }

size_t DistributedField::totlatlen() const { return domain_.jsize; }

NetCDFDumper &MsgRepo::getNetcdfDumper() { return netcdfDumper_; }
