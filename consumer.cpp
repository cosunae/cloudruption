#include "Config.h"
#include "Field.h"
#include "KeyMessage.h"
#include <cstring>
#include <iostream>
#include <memory>
#include <netcdf.h>
#include <rdkafka.h>
#include <rdkafkacpp.h>
#include <stdint.h>
#include <string>
#include <unordered_map>

#include "nctools.h"

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
              size_t levlen, float *data)
      : ilonstart_(ilonstart), jlatstart_(jlatstart), lonlen_(lonlen),
        latlen_(latlen), levlen_(levlen) {
    data_ =
        static_cast<float *>(malloc(lonlen * latlen * levlen * sizeof(float)));
    memcpy(data_, data, lonlen * latlen * levlen * sizeof(float));
  }
  // TODO fix this
  //  ~SinglePatch() { free(data_); }

  size_t ilonStart() { return ilonstart_; }
  size_t jlatStart() { return jlatstart_; }
  size_t lonlen() { return lonlen_; }
  size_t latlen() { return latlen_; }
  size_t levlen() { return levlen_; }
  float operator()(int i, int j, int k) {
    return data_[k * lonlen_ * latlen_ + j * lonlen_ + i];
  }

private:
  size_t ilonstart_, jlatstart_;
  size_t lonlen_, latlen_, levlen_;

  float *data_;
};

class DistributedField {
public:
  DistributedField(size_t npatches, const size_t lonlen, const size_t latlen,
                   const size_t levlen)
      : npatches_(npatches), totlonlen_(lonlen), totlatlen_(latlen),
        levlen_(levlen) {}

  void insertPatch(size_t ilonstart, size_t jlatstart, size_t lonlen,
                   size_t latlen, float *data) {
    patches_.push_back(std::move(
        SinglePatch{ilonstart, jlatstart, lonlen, latlen, levlen_, data}));
  }
  void writeIfComplete() {
    if (npatches_ != patches_.size())
      return;

    std::vector<float> fullfield(totlonlen_ * totlatlen_ * levlen_);

    int nextilon = 0;
    int nextjlat = 0;

    while (nextilon < totlonlen_ || nextjlat < totlatlen_) {
      for (auto &patch : patches_) {
        if (patch.ilonStart() == nextilon && patch.jlatStart() == nextjlat) {
          for (int k = 0; k < patch.levlen(); ++k) {
            for (int j = 0; j < patch.latlen(); ++j) {
              for (int i = 0; i < patch.lonlen(); ++i) {
                fullfield[k * totlonlen_ * totlatlen_ +
                          (j + patch.jlatStart()) * totlonlen_ +
                          (i + patch.ilonStart())] = patch(i, j, k);
              }
            }
          }
          nextilon += patch.lonlen();
          if (nextilon == totlonlen_) {
            nextjlat += patch.latlen();
            if (nextjlat != totlatlen_)
              nextilon = 0;
          }
          continue;
        }
      }
    }
    DomainConf domain{0, 0, totlonlen_, totlatlen_, levlen_, 0, 0};
    FieldProp fieldProp = makeDomainFieldProp(domain);
    netcdfDump(0, fullfield.data(), fieldProp, "consumll");
  }

private:
  size_t npatches_, totlonlen_, totlatlen_, levlen_;
  std::vector<SinglePatch> patches_;
};

class MsgRepo {
public:
  const std::unique_ptr<DistributedField> &
  getDistField(const KeyMessage &keyMsg) {
    if (!msgs_.count(keyMsg.key)) {
      msgs_.emplace(std::make_pair(keyMsg.key,
                                   std::move(std::make_unique<DistributedField>(
                                       keyMsg.npatches, keyMsg.totlonlen,
                                       keyMsg.totlatlen, keyMsg.levlen))));
    }
    return msgs_.at(keyMsg.key);
  }

private:
  std::unordered_map<std::string, std::unique_ptr<DistributedField>> msgs_;
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
    std::cout << "Key: " << key.myrank << ":" << key.latlen << " " << key.lonlen
              << " ; lon:" << key.ilon_start << ", lat:" << key.jlat_start
              << std::endl;
    if (verbosity >= 1) {
      printf("%.*s\n", static_cast<int>(message->len()),
             static_cast<const char *>(message->payload()));
    }

    const auto &field = msgRepo.getDistField(key);
    field->insertPatch(key.ilon_start, key.jlat_start, key.lonlen, key.latlen,
                       static_cast<float *>(message->payload()));

    field->writeIfComplete();
    DomainConf domain{0, 0, key.lonlen, key.latlen, key.levlen, 0, 0};
    FieldProp fieldProp = makeDomainFieldProp(domain);
    netcdfDump(key.myrank, static_cast<float *>(message->payload()), fieldProp,
               "consum");
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

  MsgRepo msgRepo;
  /*
   * Consume messages
   */
  while (run) {
    RdKafka::Message *msg = consumer->consume(1000);

    msg_consume(msg, msgRepo);
    delete msg;
  }
}
