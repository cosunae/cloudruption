#pragma once

#include "Grid.h"
#include <cassert>
#include <numeric>
#include <vector>

struct FieldProp {
  FieldProp(const std::vector<size_t> &strides,
            const std::vector<size_t> &sizes)
      : strides_(strides), sizes_(sizes),
        totalsize_(
            std::accumulate(std::next(sizes.begin()), sizes.end(),
                            sizes.at(0), // start with first element
                            [](size_t tot, size_t el) { return tot * el; })) {}

  size_t idx(std::vector<size_t> pos);
  std::vector<size_t> strides_;
  std::vector<size_t> sizes_;
  size_t totalsize_;

  const std::vector<size_t> &getSizes() { return sizes_; }
};

FieldProp makeGlobalFieldProp(GridConf const &gridconf);
FieldProp makeDomainFieldProp(DomainConf const &domain);
FieldProp makePatchFieldProp(GridConf const &gridconf);
