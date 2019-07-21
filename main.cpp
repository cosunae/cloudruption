#include <iostream>
#include <mpi.h>
#include <netcdf.h>
#include <rdkafka.h>
#include <string>

/* Handle errors by printing an error message and exiting with a
 * non-zero status. */
#define ERR(e)                                                                 \
  {                                                                            \
    printf("Error: %s\n", nc_strerror(e));                                     \
    return 2;                                                                  \
  }

/**
 * @brief Message delivery report callback.
 *
 * This callback is called exactly once per message, indicating if
 * the message was succesfully delivered
 * (rkmessage->err == RD_KAFKA_RESP_ERR_NO_ERROR) or permanently
 * failed delivery (rkmessage->err != RD_KAFKA_RESP_ERR_NO_ERROR).
 *
 * The callback is triggered from rd_kafka_poll() and executes on
 * the application's thread.
 */
static void dr_msg_cb(rd_kafka_t *rk, const rd_kafka_message_t *rkmessage,
                      void *opaque) {
  if (rkmessage->err)
    fprintf(stderr, "%% Message delivery failed: %s\n",
            rd_kafka_err2str(rkmessage->err));
  else
    fprintf(stderr,
            "%% Message delivered (%zd bytes, "
            "partition %" PRId32 ")\n",
            rkmessage->len, rkmessage->partition);

  /* The rkmessage is destroyed automatically by librdkafka */
}

int main(int argc, char **argv) {
  MPI_Init(&argc, &argv);

  int myrank, mpisize;
  MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
  MPI_Comm_size(MPI_COMM_WORLD, &mpisize);

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

    std::cout << "KKK " << levid << std::endl;
    size_t latlen, len, lonlen, levlen;
    if ((retval = nc_inq_dimlen(ncid, latid, &latlen)))
      ERR(retval)
    if ((retval = nc_inq_dimlen(ncid, lonid, &lonlen)))
      ERR(retval)

    if ((retval = nc_inq_dimlen(ncid, levid, &levlen)))
      ERR(retval)

    size_t levelsize = latlen * lonlen * sizeof(float);
    size_t fieldsize = levelsize * levlen;

    float *u = (float *)malloc(fieldsize);

    int uid;
    if ((retval = nc_inq_varid(ncid, "u", &uid)))
      ERR(retval);

    size_t startv[4] = {0, 0, 0, 0};
    size_t countv[4] = {1, levlen, latlen, lonlen};

    if ((retval = nc_get_vara_float(ncid, uid, startv, countv, u)))
      ERR(retval);
    if ((retval = nc_close(ncid)))
      ERR(retval);

    std::cout << "Lon : " << lonlen << " lat: " << latlen << " lev : " << levlen
              << std::endl;
    //  }

    rd_kafka_conf_t *conf;
    char errstr[512];

    conf = rd_kafka_conf_new();
    char broker[] = "localhost:9092";

    /* Set bootstrap broker(s) as a comma-separated list of
     * host or host:port (default port 9092).
     * librdkafka will use the bootstrap brokers to acquire the full
     * set of brokers from the cluster. */
    if (rd_kafka_conf_set(conf, "bootstrap.servers", broker, errstr,
                          sizeof(errstr)) != RD_KAFKA_CONF_OK) {
      fprintf(stderr, "%s\n", errstr);
      return 1;
    }

    /* Set the delivery report callback.
     * This callback will be called once per message to inform
     * the application if delivery succeeded or failed.
     * See dr_msg_cb() above. */
    rd_kafka_conf_set_dr_msg_cb(conf, dr_msg_cb);

    /*
     * Create producer instance.
     *
     * NOTE: rd_kafka_new() takes ownership of the conf object
     *       and the application must not reference it again after
     *       this call.
     */
    rd_kafka_t *rk =
        rd_kafka_new(RD_KAFKA_PRODUCER, conf, errstr, sizeof(errstr));
    if (!rk) {
      fprintf(stderr, "%% Failed to create new producer: %s\n", errstr);
      return 1;
    }

    /* Create topic object that will be reused for each message
     * produced.
     *
     * Both the producer instance (rd_kafka_t) and topic objects (topic_t)
     * are long-lived objects that should be reused as much as possible.
     */
    const char topic[] = "test2";
    rd_kafka_topic_t *rkt; /* Topic object */
    rkt = rd_kafka_topic_new(rk, topic, NULL);
    if (!rkt) {
      fprintf(stderr, "%% Failed to create topic object: %s\n",
              rd_kafka_err2str(rd_kafka_last_error()));
      rd_kafka_destroy(rk);
      return 1;
    }

    if (rd_kafka_produce(
            /* Topic object */
            rkt,
            /* Use builtin partitioner to select partition*/
            RD_KAFKA_PARTITION_UA,
            /* Make a copy of the payload. */
            RD_KAFKA_MSG_F_COPY,
            /* Message payload (value) and length */
            u, levelsize,
            /* Optional key and its length */
            NULL, 0,
            /* Message opaque, provided in
             * delivery report callback as
             * msg_opaque. */
            NULL) == -1) {
      /**
       * Failed to *enqueue* message for producing.
       */
      fprintf(stderr, "%% Failed to produce to topic %s: %s\n",
              rd_kafka_topic_name(rkt),
              rd_kafka_err2str(rd_kafka_last_error()));
    }
  }
  MPI_Finalize();
}
