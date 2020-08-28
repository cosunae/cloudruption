#include <algorithm>
#include "../KafkaProducer.h"

extern "C"
{
    KafkaProducer *create_producer(const char *broker, const char *product)
    {
        KafkaProducer *producer = new KafkaProducer(broker, product);
        return producer;
    }

    void produce(KafkaProducer *producer, KeyMessage &key, float *data, size_t &datasize,
                 const char *topic)
    {
        producer->produce(key, data, datasize, topic);
    }
}
