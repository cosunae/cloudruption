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
    std::ifstream fin(jsonConfigFile_);
    if (!fin.is_open()) {
      throw std::runtime_error("cannot to open config file " + jsonConfigFile_);
    }
    fin >> config;

    if (!config.count("topics")) {
      throw std::runtime_error("topics not found in config");
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

  std::string getKafkaBroker() {
    nlohmann::json config;
    std::ifstream fin(jsonConfigFile_);
    if (!fin.is_open()) {
      throw std::runtime_error("cannot to open config file " + jsonConfigFile_);
    }
    fin >> config;

    if (!config.count("files")) {
      throw std::runtime_error("files not found in config");
    }
    std::string result = config["kafkaBroker"].get<std::string>();
    return result;
  }

  std::vector<std::string> getFiles() {
    nlohmann::json config;
    std::ifstream fin(jsonConfigFile_);
    if (!fin.is_open()) {
      throw std::runtime_error("cannot to open config file " + jsonConfigFile_);
    }
    fin >> config;

    if (!config.count("files")) {
      throw std::runtime_error("files not found in config");
    }
    std::vector<std::string> files;

    auto files_cfg = config["files"];
    std::cout << "Producing files :" << std::endl;
    for (auto file : files_cfg) {
      auto val = file.get<std::string>();
      std::cout << "...  " << val << std::endl;
      files.push_back(val);
    }
    return files;
  }
};
