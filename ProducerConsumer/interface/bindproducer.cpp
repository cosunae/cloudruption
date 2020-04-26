#include <algorithm>
#include "../KafkaProducer.h"

static inline void ltrim(std::string &s)
{
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), [](int ch) {
                return !std::isspace(ch);
            }));
}
// trim from end (in place)
static inline void rtrim(std::string &s)
{
    s.erase(std::find_if(s.rbegin(), s.rend(), [](int ch) {
                return !std::isspace(ch);
            }).base(),
            s.end());
}
extern "C"
{
    KafkaProducer *create_producer(const char *broker)
    {
        KafkaProducer *producer = new KafkaProducer(broker);
        producer->test();
        return producer;
    }

    void produce(KafkaProducer *producer, KeyMessage &key, float *data, size_t &datasize,
                 const char *fieldname)
    {
        producer->test();
        std::string fieldnamet = std::string(fieldname, 32);
        rtrim(fieldnamet);
        producer->produce(key, data, datasize, fieldnamet);
    }
}
