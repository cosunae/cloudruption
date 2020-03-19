#include "json.hpp"
#include <fstream>
#include <vector>

class Config {
private:
  std::string jsonConfigFile_;
  nlohmann::json config_;

public:
  Config(std::string configfile) : jsonConfigFile_(configfile) {
    std::ifstream fin(jsonConfigFile_);
    if (!fin.is_open()) {
      throw std::runtime_error("cannot to open config file " + jsonConfigFile_);
    }
    fin >> config_;
  }

  std::vector<std::string> getTopics() {
    if (!config_.count("topics")) {
      throw std::runtime_error("topics not found in config");
    }
    std::vector<std::string> topics;

    auto topics_cfg = config_["topics"];
    std::cout << "Subscribing to topics :" << std::endl;
    for (auto topic : topics_cfg) {
      auto val = topic.get<std::string>();
      std::cout << "...  " << val << std::endl;
      topics.push_back(val);
    }
    return topics;
  }

  template <typename T> T get(std::string key) {
    if (!config_.count(key)) {
      throw std::runtime_error(key + " not found in config");
    }
    T result = config_[key].get<T>();
    return result;
  }

  bool has(std::string key) { return config_.count(key); }

  std::vector<std::string> getFiles() {
    if (!config_.count("files")) {
      throw std::runtime_error("files not found in config");
    }
    std::vector<std::string> files;

    auto files_cfg = config_["files"];
    std::cout << "Producing files :" << std::endl;
    for (auto file : files_cfg) {
      auto val = file.get<std::string>();
      std::cout << "...  " << val << std::endl;
      files.push_back(val);
    }
    return files;
  }
};
