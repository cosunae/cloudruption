#include "Config.h"
#include "KeyMessage.h"
#include "SinglePatch.h"
#include <assert.h>
#include <bits/stdc++.h>
#include <chrono>
#include <iostream>
#include <limits.h>
#include <math.h>
#include <mpi.h>
#include <netcdf.h>
#include <numeric>
#include <rdkafkacpp.h>
#include <stdint.h>
#include <string>
#include <vector>

#include "FieldProp.h"
#include "Grid.h"

#if SIZE_MAX == UCHAR_MAX
#define MPI_SIZE_T MPI_UNSIGNED_CHAR
#elif SIZE_MAX == USHRT_MAX
#define MPI_SIZE_T MPI_UNSIGNED_SHORT
#elif SIZE_MAX == UINT_MAX
#define MPI_SIZE_T MPI_UNSIGNED
#elif SIZE_MAX == ULONG_MAX
#define MPI_SIZE_T MPI_UNSIGNED_LONG
#elif SIZE_MAX == ULLONG_MAX
#define MPI_SIZE_T MPI_UNSIGNED_LONG_LONG
#else
#error "Unknown TYPE"
#endif

/* Handle errors by printing an error message and exiting with a
 * non-zero status. */
#define ERR(e)                                                                 \
  {                                                                            \
    printf("Error: %s\n", nc_strerror(e));                                     \
    return e;                                                                  \
  }
#define ERRC(e)                                                                \
  {                                                                            \
    printf("Error: %s\n", nc_strerror(e));                                     \
    ierror = e;                                                                \
  }

class ExampleEventCb : public RdKafka::EventCb {
public:
  void event_cb(RdKafka::Event &event) {
    switch (event.type()) {
    case RdKafka::Event::EVENT_ERROR:
      //      if (event.fatal()) {
      //        std::cerr << "FATAL ";
      //        run = false;
      //      }
      std::cerr << "ERROR (" << RdKafka::err2str(event.err())
                << "): " << event.str() << std::endl;
      break;

    case RdKafka::Event::EVENT_STATS:
      std::cerr << "\"STATS\": " << event.str() << std::endl;
      break;

    case RdKafka::Event::EVENT_LOG:
      fprintf(stderr, "LOG-%i-%s: %s\n", event.severity(), event.fac().c_str(),
              event.str().c_str());
      break;

    default:
      std::cerr << "EVENT " << event.type() << " ("
                << RdKafka::err2str(event.err()) << "): " << event.str()
                << std::endl;
      break;
    }
  }
};

class ExampleDeliveryReportCb : public RdKafka::DeliveryReportCb {
public:
  void dr_cb(RdKafka::Message &message) {
    // TODO recover from master
    std::string status_name;
    //    switch (message.()) {
    //    case RdKafka::Message::MSG_STATUS_NOT_PERSISTED:
    //      status_name = "NotPersisted";
    //      break;
    //    case RdKafka::Message::MSG_STATUS_POSSIBLY_PERSISTED:
    //      status_name = "PossiblyPersisted";
    //      break;
    //    case RdKafka::Message::MSG_STATUS_PERSISTED:
    //      status_name = "Persisted";
    //      break;
    //    default:
    //      status_name = "Unknown?";
    //      break;
    //    }
    std::cout << "Message delivery for (" << message.len()
              << " bytes): " << status_name << ": " << message.errstr()
              << std::endl;
    if (message.key())
      std::cout << "Key: " << *(message.key()) << ";" << std::endl;
  }
};

void mpierror() { MPI_Abort(MPI_COMM_WORLD, -1); }

class FieldHandler {
  const int mpirank_, mpisize_;
  std::string filename_;
  GridConf gridconf_;
  SubDomainConf subdomainconf_;
  std::optional<FieldDesc> globalFieldProp_;
  std::optional<FieldDesc> domainFieldProp_;
  std::optional<FieldDesc> patchFieldProp_;

  field3d *fglob_ = nullptr;
  field3d *fsubd_ = nullptr;

public:
  FieldHandler(int mpirank, int mpisize, std::string filename)
      : mpirank_(mpirank), mpisize_(mpisize), filename_(filename) {}

  int setupGridConf(std::string field) {
    if (mpirank_ == 0) {

      // domain decomposition as
      // 0 1 2
      // 3 4 5

      float a = std::sqrt(mpisize_);
      for (int i = (int)a; i > 0; --i) {
        if (mpisize_ % i == 0) {
          gridconf_.nbx = i;
          gridconf_.nby = mpisize_ / gridconf_.nbx;
          break;
        }
      }

      if (gridconf_.nbx == -1 || gridconf_.nby == -1) {
        throw std::runtime_error(
            "Error: could not find a valid domain decomposition");
      }

      int ierror;
      int retval;
      int ncid;
      if ((retval = nc_open(filename_.c_str(), NC_NOWRITE, &ncid)))
        ERRC(retval);

      int vid;
      if ((retval = nc_inq_varid(ncid, field.c_str(), &vid)))
        ERR(retval);

      int ndims;
      if ((retval = nc_inq_varndims(ncid, vid, &ndims)))
        ERRC(retval);

      if (ndims != 4)
        throw std::runtime_error("Other than 3D fields not yet supported :" +
                                 std::to_string(ndims));

      int dims[4];
      if ((retval = nc_inq_vardimid(ncid, vid, dims)))
        ERRC(retval);

      if ((retval = nc_inq_dimlen(ncid, dims[3], &gridconf_.lonlen)))
        ERRC(retval)

      if ((retval = nc_inq_dimlen(ncid, dims[2], &gridconf_.latlen)))
        ERRC(retval)

      if ((retval = nc_inq_dimlen(ncid, dims[1], &gridconf_.levlen)))
        ERRC(retval)
      gridconf_.isizepatch =
          (gridconf_.lonlen + gridconf_.nbx - 1) / gridconf_.nbx;

      gridconf_.jsizepatch =
          (gridconf_.latlen + gridconf_.nby - 1) / gridconf_.nby;

      if ((retval = nc_close(ncid)))
        ERRC(retval);
    }
    MPI_Bcast(&gridconf_, sizeof(GridConf) / sizeof(size_t), MPI_SIZE_T, 0,
              MPI_COMM_WORLD);

    subdomainconf_.levels = gridconf_.levlen;

    size_t nx = mpirank_ % gridconf_.nbx;
    size_t ny = mpirank_ / gridconf_.nbx;

    gridconf_.isizepatch =
        (gridconf_.lonlen + gridconf_.nbx - 1) / gridconf_.nbx;
    subdomainconf_.istart = nx * gridconf_.isizepatch;
    subdomainconf_.isize = std::min(gridconf_.isizepatch,
                                    gridconf_.lonlen - subdomainconf_.istart);

    gridconf_.jsizepatch =
        (gridconf_.latlen + gridconf_.nby - 1) / gridconf_.nby;
    subdomainconf_.jstart = ny * gridconf_.jsizepatch;
    subdomainconf_.jsize = std::min(gridconf_.jsizepatch,
                                    gridconf_.latlen - subdomainconf_.jstart);

    globalFieldProp_ = makeGlobalFieldProp(gridconf_);
    domainFieldProp_ = makeDomainFieldProp(subdomainconf_);
    patchFieldProp_ = makePatchFieldProp(gridconf_);

    if (mpirank_ == 0) {
      if (fglob_)
        free(fglob_);

      size_t levelsize = gridconf_.latlen * gridconf_.lonlen * sizeof(float);
      size_t fieldsize = levelsize * gridconf_.levlen;

      fglob_ =
          new field3d(gridconf_.lonlen, gridconf_.latlen, gridconf_.levlen);
    }
    return 0;
  }

  int getMpiRank() const { return mpirank_; }
  int getMpiSize() const { return mpisize_; }
  FieldDesc getGlobalFieldProp() const { return globalFieldProp_.value(); }
  FieldDesc getDomainFieldProp() const { return domainFieldProp_.value(); }
  const SubDomainConf &getSubdomainconf() const { return subdomainconf_; }
  const GridConf &getGridconf() const { return gridconf_; }

  field3d &getSubdomainField() const {
    assert(fsubd_);
    return *fsubd_;
  }

  void printConf() {
    if (mpirank_ == 0) {
      std::cout << "------------  domain conf ------------" << std::endl;
      std::cout << "nbx : " << gridconf_.nbx << std::endl;
      std::cout << "nby : " << gridconf_.nby << std::endl;

      gridconf_.print();
    }
  }
  int loadField(std::string field) {
    if (mpirank_ == 0) {
      int retval;
      int ncid;
      if ((retval = nc_open(filename_.c_str(), NC_NOWRITE, &ncid)))
        ERR(retval);

      int uid;
      if ((retval = nc_inq_varid(ncid, field.c_str(), &uid)))
        ERR(retval);

      // only loaded for rank = 0
      size_t startv[4] = {0, 0, 0, 0};
      size_t countv[4] = {1, gridconf_.levlen, gridconf_.latlen,
                          gridconf_.lonlen};

      if ((retval =
               nc_get_vara_float(ncid, uid, startv, countv, fglob_->data())))
        ERR(retval);

      if ((retval = nc_close(ncid)))
        ERR(retval);
    }

    printConf();
    scatterSubdomains();

    return 0;
  }

  void scatterSubdomains() {
    field3d ft(patchFieldProp_->getSizes()[0], patchFieldProp_->getSizes()[1],
               patchFieldProp_->getSizes()[2]);

    float *fscat = nullptr;
    if (mpirank_ == 0) {
      size_t istridet = 1;
      size_t jstridet = istridet * gridconf_.isizepatch;
      size_t kstridet = jstridet * gridconf_.jsizepatch;
      size_t bistridet = kstridet * gridconf_.levlen;
      size_t bjstridet = bistridet * gridconf_.nbx;

      // temporary field to prepare all the blocks
      fscat = (float *)malloc(patchFieldProp_->totalsize_ * gridconf_.nbx *
                              gridconf_.nby * sizeof(float));
      for (int bj = 0; bj < gridconf_.nby; ++bj) {
        for (int bi = 0; bi < gridconf_.nbx; ++bi) {
          for (int k = 0; k < gridconf_.levlen; ++k) {
            for (int j = 0; j < gridconf_.jsizepatch; ++j) {
              for (int i = 0; i < gridconf_.isizepatch; ++i) {

                size_t iglb = bi * gridconf_.isizepatch + i;
                size_t jglb = bj * gridconf_.jsizepatch + j;
                if (iglb > gridconf_.lonlen || jglb > gridconf_.latlen)
                  continue;

                if (i * istridet + j * jstridet + k * kstridet +
                        bi * bistridet + bj * bjstridet >=
                    patchFieldProp_->totalsize_ * gridconf_.nbx *
                        gridconf_.nby * sizeof(float)) {
                  mpierror();
                  throw std::runtime_error("ERROR out of bound");
                }
                if (iglb * globalFieldProp_->strides_[0] +
                        jglb * globalFieldProp_->strides_[1] +
                        k * globalFieldProp_->strides_[2] >=
                    globalFieldProp_->totalsize_ * sizeof(float)) {
                  mpierror();
                  throw std::runtime_error("ERROR out of bound");
                }

                fscat[i * istridet + j * jstridet + k * kstridet +
                      bi * bistridet + bj * bjstridet] =
                    (*fglob_)(iglb, jglb, (size_t)k);
              }
            }
          }
        }
      }
    }

    MPI_Scatter(fscat,
                gridconf_.isizepatch * gridconf_.jsizepatch * gridconf_.levlen,
                MPI_FLOAT, ft.data(),
                gridconf_.isizepatch * gridconf_.jsizepatch * gridconf_.levlen,
                MPI_FLOAT, 0, MPI_COMM_WORLD);

    if (mpirank_ == 0) {
      free(fscat);
    }
    if (fsubd_) {
      free(fsubd_);
    }
    fsubd_ = new field3d(subdomainconf_.isize, subdomainconf_.jsize,
                         subdomainconf_.levels);

    for (size_t k = 0; k < gridconf_.levlen; ++k) {
      for (size_t j = 0; j < subdomainconf_.jsize; ++j) {
        for (size_t i = 0; i < subdomainconf_.isize; ++i) {
          (*fsubd_)(i, j, k) = ft(i, j, k);
        }
      }
    }
  }
};

class KafkaProducer {
  /*
   * Create configuration objects
   */
  RdKafka::Conf *conf_;
  const int32_t partition_ = RdKafka::Topic::PARTITION_UA;
  const std::string broker_;
  FieldHandler &fHandler_;

  RdKafka::Producer *producer_;
  ExampleDeliveryReportCb ex_dr_cb_;
  ExampleEventCb ex_event_cb_;

public:
  KafkaProducer(FieldHandler &fieldHandler,
                std::string broker = "localhost:9092")
      : conf_(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL)),
        broker_(broker), fHandler_(fieldHandler) {
    std::string errstr;

    /*
     * Set configuration properties
     */
    if (conf_->set("metadata.broker.list", broker_, errstr) !=
        RdKafka::Conf::CONF_OK) {
      std::cerr << errstr << std::endl;
      exit(1);
    }

    conf_->set("event_cb", &ex_event_cb_, errstr);

    //  if (conf->set("group.id", "group1", errstr) != RdKafka::Conf::CONF_OK) {
    //    std::cerr << errstr << std::endl;
    //    exit(1);
    //  }

    //  auto dump = conf->dump();
    //  for (std::list<std::string>::iterator it = dump->begin();
    //       it != dump->end();) {
    //    std::cout << *it << " = ";
    //    it++;
    //    std::cout << *it << std::endl;
    //    it++;
    //  }
    //  std::cout << std::endl;

    /* Set delivery report callback */
    conf_->set("dr_cb", &ex_dr_cb_, errstr);

    /*
     * Create producer using accumulated global configuration.
     */
    producer_ = RdKafka::Producer::create(conf_, errstr);
    if (!producer_) {
      std::cerr << "Failed to create producer: " << errstr << std::endl;
      exit(1);
    }

    std::cout << "% Created producer " << producer_->name() << std::endl;
  }

  KeyMessage getMsgKey(ActionType actionType, size_t timestamp,
                       std::string fieldname, const size_t lev) const {
    const auto &subdomainconf = fHandler_.getSubdomainconf();
    auto domainFieldProp = fHandler_.getDomainFieldProp();
    const auto &gridconf = fHandler_.getGridconf();

    const float dx = 60;

    KeyMessage key{
        actionType, "", fHandler_.getMpiSize(), fHandler_.getMpiRank(),
        timestamp, subdomainconf.istart, subdomainconf.jstart, lev,
        domainFieldProp.sizes_[0], domainFieldProp.sizes_[1],
        domainFieldProp.sizes_[2], gridconf.lonlen, gridconf.latlen,
        // emulating staggering
        (fieldname == "U" ? dx / 2 : 0),
        dx * (domainFieldProp.sizes_[0] - 1) + (fieldname == "U" ? dx / 2 : 0),
        (fieldname == "V" ? dx / 2 : 0),
        dx * (domainFieldProp.sizes_[1] - 1) + (fieldname == "V" ? dx / 2 : 0)};
    strcpy(key.key, fieldname.substr(0, 8).c_str());
    return key;
  }

  void sendHeader(std::string filename, size_t timestamp,
                  std::string fieldname) {
    std::cout << "Sending header for topic: " << fieldname << std::endl;
    auto key = getMsgKey(ActionType::HeaderData, timestamp, fieldname, -1);

    TopicHeader headerData;
    strcpy(
        headerData.filename,
        filename.substr(0, std::min((size_t)(256), filename.length())).c_str());

    std::string topic = std::string("cosmo_")+fieldname;

    RdKafka::ErrorCode resp = producer_->produce(
        topic, partition_,
        RdKafka::Producer::RK_MSG_COPY /* Copy payload */,
        /* Value */
        static_cast<void *>(&(headerData)), sizeof(headerData),
        /* Key */
        &key, sizeof(KeyMessage),
        /* Timestamp (defaults to now) */
        0, NULL);

    if (resp != RdKafka::ERR_NO_ERROR) {
      std::cerr << "% Produce failed: " << RdKafka::err2str(resp) << std::endl;
    } else {
      std::cerr << "% Produced Header msg for filename " << filename
                << std::endl;
    }
  }

  void sendClose(std::string filename, size_t timestamp,
                 std::string fieldname) {
    std::cout << "Sending close for topic: " << fieldname << std::endl;
    auto key = getMsgKey(ActionType::EndData, timestamp, fieldname, -2);

    TopicHeader headerData;
    strcpy(
        headerData.filename,
        filename.substr(0, std::min((size_t)(256), filename.length())).c_str());

    std::string topic = std::string("cosmo_")+fieldname;

    RdKafka::ErrorCode resp = producer_->produce(
        topic, partition_,
        RdKafka::Producer::RK_MSG_COPY /* Copy payload */,
        /* Value */
        static_cast<void *>(&(headerData)), sizeof(headerData),
        /* Key */
        &key, sizeof(KeyMessage),
        /* Timestamp (defaults to now) */
        0, NULL);

    if (resp != RdKafka::ERR_NO_ERROR) {
      std::cerr << "% Produce failed: " << RdKafka::err2str(resp) << std::endl;
    } else {
      std::cerr << "% Produced Header msg for filename " << filename
                << std::endl;
    }
  }

  void produce(size_t timestamp, std::string fieldname, size_t lev) {
    auto key = getMsgKey(ActionType::Data, timestamp, fieldname, lev);

    for (int i = 0; i < fHandler_.getMpiSize(); ++i) {
      if (i == fHandler_.getMpiRank()) {
        /*
         * Produce message
         */

        std::string topic = std::string("cosmo_")+fieldname;

        RdKafka::ErrorCode resp = producer_->produce(
            topic, partition_,
            RdKafka::Producer::RK_MSG_COPY /* Copy payload */,
            /* Value */
            static_cast<void *>(&(fHandler_.getSubdomainField()(0, 0, lev))),
            fHandler_.getDomainFieldProp().getSizes()[0] *
                fHandler_.getDomainFieldProp().getSizes()[1] * sizeof(float),
            /* Key */
            &key, sizeof(KeyMessage),
            /* Timestamp (defaults to now) */
            0, NULL);

        if (resp != RdKafka::ERR_NO_ERROR) {
          std::cerr << "% Produce failed: " << RdKafka::err2str(resp)
                    << std::endl;
        } else {
          auto subdomainconf = fHandler_.getSubdomainconf();
          std::cerr << "% Produced message ("
                    << subdomainconf.isize * subdomainconf.jsize *
                           subdomainconf.levels * sizeof(float)
                    << " bytes)" << std::endl;
        }
        producer_->poll(0);

        while (producer_->outq_len() > 0) {
          std::cerr << "Waiting for " << producer_->outq_len() << std::endl;
          producer_->poll(1000);
        }
      }
      MPI_Barrier(MPI_COMM_WORLD);
    }
  }
};

int main(int argc, char **argv) {
  MPI_Init(&argc, &argv);

  int myrank, mpisize;

  Config config;
  auto topics = config.getTopics();

  MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
  MPI_Comm_size(MPI_COMM_WORLD, &mpisize);

  auto files = config.getFiles();

  for (auto file : files) {
    FieldHandler fieldHandler(myrank, mpisize, file);

    KafkaProducer producer(fieldHandler, config.getKafkaBroker());

    std::chrono::system_clock::time_point p = std::chrono::system_clock::now();
    std::time_t tt = std::chrono::system_clock::to_time_t(p);
    size_t t = static_cast<size_t>(tt);

    for (auto fieldname : topics) {
      if (fieldHandler.setupGridConf(fieldname))
        throw std::runtime_error("Error setting up grid");

      producer.sendHeader(file, t, fieldname);
      fieldHandler.loadField(fieldname);

      for (size_t k = 0; k < fieldHandler.getGridconf().levlen; ++k) {
        producer.produce(t, fieldname, k);
      }

      // right now a single close signal from one mpi rank will close the file
      // of the topic. therefore we need to synchronize all mpi ranks to make
      // sure that
      MPI_Barrier(MPI_COMM_WORLD);
      producer.sendClose(file, t, fieldname);
    }
  }

  MPI_Finalize();
}
