#pragma once

#include "Grid.h"
#include <cassert>
#include <numeric>
#include <string>
#include <vector>

struct FieldDesc {
  FieldDesc(const std::vector<size_t> &strides,
            const std::vector<size_t> &sizes)
      : strides_(strides), sizes_(sizes),
        totalsize_(
            std::accumulate(std::next(sizes.begin()), sizes.end(),
                            sizes.at(0), // start with first element
                            [](size_t tot, size_t el) { return tot * el; })) {}

  std::vector<size_t> strides_;
  std::vector<size_t> sizes_;
  size_t totalsize_;

  const std::vector<size_t> &getSizes() { return sizes_; }
};

struct FieldProp {
  FieldProp(std::string variableName, FieldDesc fieldProp)
      : variableName_(variableName), fieldProp_(fieldProp) {}
  std::string variableName_;
  FieldDesc fieldProp_;
};

FieldDesc makeGlobalFieldProp(GridConf const &gridconf);
FieldDesc makeDomainFieldProp(DomainConf const &domain);
FieldDesc makePatchFieldProp(GridConf const &gridconf);
FieldProp makeDomainField(std::string variableName, DomainConf const &domain);
