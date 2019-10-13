#include "json.hpp"
#include <fstream>
#include <vector>

class Config {
private:
  std::string jsonConfigFile_;

public:
  Config() : jsonConfigFile_("config.json") {}

  std::vector<std::string> getTopics() {
    nlohmann::json config;
    std::ifstream fin("config.json");
    if (!fin.is_open()) {
      throw("cannot to open config file config.json");
    }
    fin >> config;

    if (!config.count("topics")) {
      throw("topics not found in config");
    }
    std::vector<std::string> topics;

    auto topics_cfg = config["topics"];
    std::cout << "Subscribing to topics :" << std::endl;
    for (auto topic : topics_cfg) {
      auto val = topic.get<std::string>();
      std::cout << "...  " << val << std::endl;
      topics.push_back(val);
    }
    return topics;
  }
};
