#pragma once

#include "Grid.h"
#include <cassert>
#include <numeric>
#include <string>
#include <vector>

struct FieldProp {
  FieldProp(const std::vector<size_t> &strides,
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

struct Field {
  Field(std::string variableName, FieldProp fieldProp)
      : variableName_(variableName), fieldProp_(fieldProp) {}
  std::string variableName_;
  FieldProp fieldProp_;
};

FieldProp makeGlobalFieldProp(GridConf const &gridconf);
FieldProp makeDomainFieldProp(DomainConf const &domain);
FieldProp makePatchFieldProp(GridConf const &gridconf);
Field makeDomainField(std::string variableName, DomainConf const &domain);
