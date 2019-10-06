#include "KeyMessage.h"
#include <assert.h>
#include <bits/stdc++.h>
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

#include "Field.h"
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
    return 2;                                                                  \
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
    //    std::string status_name;
    //    switch (message.status()) {
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
    //    std::cout << "Message delivery for (" << message.len()
    //              << " bytes): " << status_name << ": " << message.errstr()
    //              << std::endl;
    //    if (message.key())
    //      std::cout << "Key: " << *(message.key()) << ";" << std::endl;
  }
};

void mpierror() { MPI_Abort(MPI_COMM_WORLD, -1); }
int main(int argc, char **argv) {
  MPI_Init(&argc, &argv);

  int myrank, mpisize;
  GridConf gridconf;
  DomainConf subdomainconf;

  MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
  MPI_Comm_size(MPI_COMM_WORLD, &mpisize);

  float a = std::sqrt(mpisize);
  for (int i = (int)a; i > 0; --i) {
    if (mpisize % i == 0) {
      gridconf.nbx = i;
      gridconf.nby = mpisize / gridconf.nbx;
      break;
    }
  }

  if (gridconf.nbx == -1 || gridconf.nby == -1) {
    std::cout << "Error: could not find a valid domain decomposition"
              << std::endl;
    mpierror();
    return -1;
  }
  subdomainconf.nx = myrank % gridconf.nbx;
  subdomainconf.ny = myrank / gridconf.nbx;

  float *uglob;
  // domain decomposition as
  // 0 1 2
  // 3 4 5
  if (myrank == 0) {
    std::string filename =
        "data/_grib2netcdf-atls13-a82bacafb5c306db76464bc7e824bb75-SfSU2a.nc";
    int retval;
    int ncid;
    if ((retval = nc_open(filename.c_str(), NC_NOWRITE, &ncid)))
      ERR(retval);

    int latid, lonid, levid;
    if ((retval = nc_inq_dimid(ncid, "latitude", &latid)))
      ERR(retval);

    if ((retval = nc_inq_dimid(ncid, "longitude", &lonid)))
      ERR(retval);

    if ((retval = nc_inq_dimid(ncid, "level", &levid)))
      ERR(retval);

    if ((retval = nc_inq_dimlen(ncid, latid, &gridconf.latlen)))
      ERR(retval)
    if ((retval = nc_inq_dimlen(ncid, lonid, &gridconf.lonlen)))
      ERR(retval)

    if ((retval = nc_inq_dimlen(ncid, levid, &gridconf.levlen)))
      ERR(retval)

    int uid;
    if ((retval = nc_inq_varid(ncid, "u", &uid)))
      ERR(retval);

    // only loaded for rank = 0
    size_t levelsize = gridconf.latlen * gridconf.lonlen * sizeof(float);
    size_t fieldsize = levelsize * gridconf.levlen;

    uglob = (float *)malloc(fieldsize);

    size_t startv[4] = {0, 0, 0, 0};
    size_t countv[4] = {1, gridconf.levlen, gridconf.latlen, gridconf.lonlen};

    if ((retval = nc_get_vara_float(ncid, uid, startv, countv, uglob)))
      ERR(retval);

    if ((retval = nc_close(ncid)))
      ERR(retval);
  }

  MPI_Bcast(&gridconf, 3, MPI_SIZE_T, 0, MPI_COMM_WORLD);

  FieldProp globalFieldProp = makeGlobalFieldProp(gridconf);
  subdomainconf.levels = gridconf.levlen;

  gridconf.isizepatch = (gridconf.lonlen + gridconf.nbx - 1) / gridconf.nbx;
  subdomainconf.istart = subdomainconf.nx * gridconf.isizepatch;
  subdomainconf.isize =
      std::min(gridconf.isizepatch, gridconf.lonlen - subdomainconf.istart);

  gridconf.jsizepatch = (gridconf.latlen + gridconf.nby - 1) / gridconf.nby;
  subdomainconf.jstart = subdomainconf.ny * gridconf.jsizepatch;
  subdomainconf.jsize =
      std::min(gridconf.jsizepatch, gridconf.latlen - subdomainconf.jstart);

  FieldProp domainFieldProp = makeDomainFieldProp(subdomainconf);
  FieldProp patchFieldProp = makePatchFieldProp(gridconf);

  if (myrank == 0) {
    std::cout << "------------  domain conf ------------" << std::endl;
    std::cout << "nbx : " << gridconf.nbx << std::endl;
    std::cout << "nby : " << gridconf.nby << std::endl;

    gridconf.print();
  }
  for (int i = 0; i < mpisize; ++i) {
    if (i == myrank) {
      std::cout << "mpirank : " << myrank << " (" << subdomainconf.nx << ""
                << "," << subdomainconf.ny << ")" << std::endl;
      std::cout << "  start: (" << subdomainconf.istart << ","
                << subdomainconf.jstart << ")" << std::endl;
      std::cout << "  size: (" << subdomainconf.isize << ","
                << subdomainconf.jsize << ")" << std::endl;
    }
    MPI_Barrier(MPI_COMM_WORLD);
  }

  float *ut = (float *)malloc(patchFieldProp.totalsize_ * sizeof(float));

  float *uscat;
  if (myrank == 0) {
    size_t istridet = 1;
    size_t jstridet = istridet * gridconf.isizepatch;
    size_t kstridet = jstridet * gridconf.jsizepatch;
    size_t bistridet = kstridet * gridconf.levlen;
    size_t bjstridet = bistridet * gridconf.nbx;

    // temporary field to prepare all the blocks
    uscat = (float *)malloc(patchFieldProp.totalsize_ * gridconf.nbx *
                            gridconf.nby * sizeof(float));
    for (int bj = 0; bj < gridconf.nby; ++bj) {
      for (int bi = 0; bi < gridconf.nbx; ++bi) {
        for (int k = 0; k < gridconf.levlen; ++k) {
          for (int j = 0; j < gridconf.jsizepatch; ++j) {
            for (int i = 0; i < gridconf.isizepatch; ++i) {

              size_t iglb = bi * gridconf.isizepatch + i;
              size_t jglb = bj * gridconf.jsizepatch + j;
              if (iglb > gridconf.lonlen || jglb > gridconf.latlen)
                continue;

              if (i * istridet + j * jstridet + k * kstridet + bi * bistridet +
                      bj * bjstridet >=
                  patchFieldProp.totalsize_ * gridconf.nbx * gridconf.nby *
                      sizeof(float)) {
                mpierror();
                throw std::runtime_error("ERROR out of bound");
              }
              if (iglb * globalFieldProp.strides_[0] +
                      jglb * globalFieldProp.strides_[1] +
                      k * globalFieldProp.strides_[2] >=
                  globalFieldProp.totalsize_ * sizeof(float)) {
                mpierror();
                throw std::runtime_error("ERROR out of bound");
              }

              uscat[i * istridet + j * jstridet + k * kstridet +
                    bi * bistridet + bj * bjstridet] =
                  uglob[globalFieldProp.idx({iglb, jglb, (size_t)k})];
            }
          }
        }
      }
    }
  }

  MPI_Scatter(uscat,
              gridconf.isizepatch * gridconf.jsizepatch * gridconf.levlen,
              MPI_FLOAT, ut,
              gridconf.isizepatch * gridconf.jsizepatch * gridconf.levlen,
              MPI_FLOAT, 0, MPI_COMM_WORLD);

  float *uf = (float *)malloc(subdomainconf.isize * subdomainconf.jsize *
                              subdomainconf.levels * sizeof(float));

  for (size_t k = 0; k < gridconf.levlen; ++k) {
    for (size_t j = 0; j < subdomainconf.jsize; ++j) {
      for (size_t i = 0; i < subdomainconf.isize; ++i) {
        uf[domainFieldProp.idx({i, j, k})] = ut[patchFieldProp.idx({i, j, k})];
      }
    }
  }

  //  netcdfDump(myrank, uf, domainFieldProp, "outf");

  /*
   * Create configuration objects
   */
  RdKafka::Conf *conf = RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL);

  std::string errstr;

  //  if (conf->set("group.id", "group1", errstr) != RdKafka::Conf::CONF_OK) {
  //    std::cerr << errstr << std::endl;
  //    exit(1);
  //  }

  int32_t partition = RdKafka::Topic::PARTITION_UA;

  std::string brokers = "localhost:9092";

  /*
   * Set configuration properties
   */
  if (conf->set("metadata.broker.list", brokers, errstr) !=
      RdKafka::Conf::CONF_OK) {
    std::cerr << errstr << std::endl;
    exit(1);
  }

  ExampleEventCb ex_event_cb;
  conf->set("event_cb", &ex_event_cb, errstr);

  //  auto dump = conf->dump();
  //  for (std::list<std::string>::iterator it = dump->begin();
  //       it != dump->end();) {
  //    std::cout << *it << " = ";
  //    it++;
  //    std::cout << *it << std::endl;
  //    it++;
  //  }
  //  std::cout << std::endl;

  ExampleDeliveryReportCb ex_dr_cb;

  /* Set delivery report callback */
  conf->set("dr_cb", &ex_dr_cb, errstr);

  /*
   * Create producer using accumulated global configuration.
   */
  RdKafka::Producer *producer = RdKafka::Producer::create(conf, errstr);
  if (!producer) {
    std::cerr << "Failed to create producer: " << errstr << std::endl;
    exit(1);
  }

  std::cout << "% Created producer " << producer->name() << " "
            << subdomainconf.istart << subdomainconf.jstart << std::endl;

  KeyMessage key{"u",
                 mpisize,
                 myrank,
                 subdomainconf.istart,
                 subdomainconf.jstart,
                 0,
                 0,
                 domainFieldProp.sizes_[0],
                 domainFieldProp.sizes_[1],
                 domainFieldProp.sizes_[2],
                 gridconf.lonlen,
                 gridconf.latlen};

  for (int i = 0; i < mpisize; ++i) {
    if (i == myrank) {
      /*
       * Produce message
       */
      RdKafka::ErrorCode resp = producer->produce(
          "test3", partition, RdKafka::Producer::RK_MSG_COPY /* Copy payload */,
          /* Value */
          static_cast<void *>(uf), domainFieldProp.totalsize_ * sizeof(float),
          //      static_cast<void *>(uf), 5 * sizeof(float),
          //      subdomainconf.isize * subdomainconf.jsize *
          //      subdomainconf.levels
          //      *
          //          sizeof(float),
          /* Key */
          &key, sizeof(KeyMessage),
          /* Timestamp (defaults to now) */
          0, NULL);

      if (resp != RdKafka::ERR_NO_ERROR) {
        std::cerr << "% Produce failed: " << RdKafka::err2str(resp)
                  << std::endl;
      } else {
        std::cerr << "% Produced message ("
                  << subdomainconf.isize * subdomainconf.jsize *
                         subdomainconf.levels * sizeof(float)
                  << " bytes)" << std::endl;
      }
      producer->poll(0);

      while (producer->outq_len() > 0) {
        std::cerr << "Waiting for " << producer->outq_len() << std::endl;
        producer->poll(1000);
      }
    }
    MPI_Barrier(MPI_COMM_WORLD);
  }

  MPI_Finalize();
}
