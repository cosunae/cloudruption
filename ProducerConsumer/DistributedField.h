#pragma once
#include "Grid.h"
#include "SinglePatch.h"
#include "nctools.h"
#include <string>
#include <vector>

class DistributedField {
  std::string fieldName_;

  DomainConf domain_;
  size_t npatches_;
  std::vector<SinglePatch> patches_;

public:
  DistributedField(std::string fieldName, DomainConf domainConf,
                   size_t npatches);

  BBox bboxPatches() const;
  void insertPatch(SinglePatch &&);
  void insertPatch(SinglePatch &);
  void writeIfComplete(NetCDFDumper &netcdfDumper);

  void gatherField(field3d &fullfield);

  size_t levlen() const;
  size_t totlonlen() const;
  size_t totlatlen() const;
};
