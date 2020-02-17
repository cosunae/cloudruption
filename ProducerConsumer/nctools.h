#pragma once

#include "Field.h"
#include <memory>
#include <set>
#include <string>
#include <unordered_map>

struct RegisteredTopics {
  std::unordered_map<std::string, bool> topicCount_;
  bool fileClosed = false;
};

class NetCDFDumper {
private:
  std::vector<std::string> topics_;
  std::unordered_map<std::string, int> topicToVarID_;
  std::unordered_map<std::string, int> topicToNCID_;
  std::unordered_map<std::string, int> filenameToNCID_;
  std::unordered_map<int, std::array<int, 3>> ncidToDims_;
  std::unordered_map<int, std::unique_ptr<RegisteredTopics>> ncidToRegTopics_;

public:
  NetCDFDumper(const std::vector<std::string> &topics) : topics_(topics) {}
  NetCDFDumper(const NetCDFDumper &) = default;

  void createFile(std::string filename, const FieldProp &field);
  void closeFile(std::string filename, std::string topic);

  void writeVar(std::string variableName, float *f);
};
