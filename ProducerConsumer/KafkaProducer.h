#pragma once
#include <iostream>
#include "KeyMessage.h"
#include <rdkafkacpp.h>

class ExampleEventCb : public RdKafka::EventCb
{
public:
    void event_cb(RdKafka::Event &event)
    {
        switch (event.type())
        {
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

class ExampleDeliveryReportCb : public RdKafka::DeliveryReportCb
{
public:
    void dr_cb(RdKafka::Message &message)
    {
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

class KafkaProducer
{
    /*
   * Create configuration objects
   */
    RdKafka::Conf *conf_;
    const int32_t partition_ = RdKafka::Topic::PARTITION_UA;
    const std::string broker_;
    const std::string product_;

    RdKafka::Producer *producer_;
    ExampleDeliveryReportCb ex_dr_cb_;
    ExampleEventCb ex_event_cb_;

public:
    KafkaProducer(std::string broker = "localhost:9092", std::string product = "");

    void produce(KeyMessage key, float *data, size_t datasize,
                 std::string fieldname) const;
};
