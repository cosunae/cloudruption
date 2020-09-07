#include <algorithm>
#include "../KafkaProducer.h"

#ifdef AWSSDK
#include <aws/core/Aws.h>
#include <aws/monitoring/CloudWatchClient.h>
#include <aws/monitoring/model/PutMetricDataRequest.h>
#endif

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

#ifdef AWSSDK
    void aws_put_metric_d(size_t value)
    {
                  std::cout << "SET ................... value" << value << std::endl;

    }
    void aws_put_metric(const char *ns, const char *metricname, size_t value)
    {
        Aws::SDKOptions options;
        Aws::InitAPI(options);
        {
            Aws::CloudWatch::CloudWatchClient cw;

            Aws::CloudWatch::Model::MetricDatum datum;
            datum.SetMetricName(metricname);
            datum.SetUnit(Aws::CloudWatch::Model::StandardUnit::Seconds);
	    std::cout << "SET ................... value" << value << std::endl;
            datum.SetValue(value);
            Aws::CloudWatch::Model::PutMetricDataRequest request;
            request.SetNamespace(ns);
            request.AddMetricData(datum);

            auto outcome = cw.PutMetricData(request);
            if (!outcome.IsSuccess())
            {
                std::cout << "Failed to put sample metric data:" << outcome.GetError().GetMessage() << std::endl;
            }
            else
            {
                std::cout << "Successfully put sample metric data" << std::endl;
            }
        }
        Aws::ShutdownAPI(options);
    }
#endif
}
