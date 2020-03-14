#include "DistributedField.h"
#include <assert.h>
#include <string>

DistributedField::DistributedField(std::string fieldName, size_t npatches,
                                   const DataDesc &datadesc)
    // TODO remove domain from here, it does not make sense and is not used
    : fieldName_(fieldName), npatches_(npatches), datadesc_(datadesc) {}

void DistributedField::insertPatch(SinglePatch &&patch) {
  patches_.push_back(std::move(patch));
}

void DistributedField::insertPatch(SinglePatch &patch) {
  patches_.push_back(patch);
}

void DistributedField::gatherField(field3d &fullfield) {
  int cnt = 0;
  auto bbox = bboxPatches();
  for (auto &patch : patches_) {
    for (int j = 0; j < patch.latlen(); ++j) {
      for (int i = 0; i < patch.lonlen(); ++i) {
        fullfield(i + patch.ilonStart() - bbox.limits_[0][0],
                  j + patch.jlatStart() - bbox.limits_[1][0],
                  patch.lev() - bbox.limits_[2][0]) = patch(i, j);
      }
    }
    cnt++;
  }
}

std::ostream &operator<<(std::ostream &os, const BBox &bb) {
  os << "[ [" << bb.limits_[0][0] << "," << bb.limits_[0][1] << "],"
     << "[" << bb.limits_[1][0] << "," << bb.limits_[1][1] << "],"
     << "[" << bb.limits_[2][0] << "," << bb.limits_[2][1] << "] ]";
  return os;
}

BBox DistributedField::bboxPatches() const {
  assert(patches_.size() > 0);

  return std::accumulate(std::next(patches_.begin()), patches_.end(),
                         patches_[0].bbox(),
                         [](const BBox &box, const SinglePatch &sp1) {
                           return sp1.bbox().boundingBox(box);
                         });
}

void DistributedField::writeIfComplete(NetCDFDumper &netcdfDumper) {
  if (npatches_ != patches_.size())
    return;

  field3d fullfield(totlonlen(), totlatlen(), levlen());

  gatherField(fullfield);
  netcdfDumper.writeVar(fieldName_, fullfield.data());

  patches_.clear();
}

size_t DistributedField::levlen() const { return datadesc_.levlen; }

size_t DistributedField::totlonlen() const { return datadesc_.totlonlen; }

size_t DistributedField::totlatlen() const { return datadesc_.totlatlen; }
