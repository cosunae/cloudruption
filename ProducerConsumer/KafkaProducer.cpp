#include "KafkaProducer.h"

KafkaProducer::KafkaProducer(std::string broker)
    : conf_(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL)),
      broker_(broker)
{
    std::string errstr;

    /*          
     * Set configuration properties
     */
    if (conf_->set("metadata.broker.list", broker_, errstr) !=
        RdKafka::Conf::CONF_OK)
    {
        std::cerr << errstr << std::endl;
        exit(1);
    }

    if (conf_->set("event_cb", &ex_event_cb_, errstr) !=
        RdKafka::Conf::CONF_OK)
    {
        std::cerr << errstr << std::endl;
        exit(1);
    }

    //    if (conf_->set("group.id", "group1", errstr) !=
    //    RdKafka::Conf::CONF_OK) {
    //      std::cerr << errstr << std::endl;
    //      exit(1);
    //    }

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
    if (conf_->set("dr_cb", &ex_dr_cb_, errstr) != RdKafka::Conf::CONF_OK)
    {
        std::cerr << errstr << std::endl;
        exit(1);
    }

    /*
     * Create producer using accumulated global configuration.
     */
    producer_ = RdKafka::Producer::create(conf_, errstr);
    if (!producer_)
    {
        std::cerr << "Failed to create producer: " << errstr << std::endl;
        exit(1);
    }

    std::cout << "% Created producer " << producer_->name() << " -> " << producer_ << std::endl;
}

void KafkaProducer::produce(KeyMessage key, float *data, size_t datasize,
                            std::string fieldname) const
{
    /*
     * Produce message
     */

    std::string topic = std::string("cosmo_") + fieldname;

    std::cout << "Producing on topic :" << topic << ", key: " << key.key << ", patches: " << key.npatches << ", data: " << data << ", size: " << datasize << " -> " << producer_ << std::endl;

    RdKafka::ErrorCode resp = producer_->produce(
        topic, partition_, RdKafka::Producer::RK_MSG_COPY /* Copy payload */,
        /* Value */
        static_cast<void *>(data), datasize,
        /* Key */
        &key, sizeof(KeyMessage),
        /* Timestamp (defaults to now) */
        0, NULL);

    if (resp != RdKafka::ERR_NO_ERROR)
    {
        std::cerr << "% Produce failed: topic [" << topic << "], partition ["
                  << partition_ << "], broker [" << broker_ << "], sizeof msg ["
                  << sizeof(KeyMessage) << "], error :" << RdKafka::err2str(resp)
                  << std::endl;
    }
    else
    {
        std::cout << "% Produced message (" << datasize << " bytes)" << std::endl;
    }
    producer_->poll(0);

    while (producer_->outq_len() > 0)
    {
        std::cerr << "Waiting for " << producer_->outq_len() << std::endl;
        producer_->poll(1000);
    }
}
