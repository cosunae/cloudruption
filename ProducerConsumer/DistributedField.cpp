#include "DistributedField.h"
#include <assert.h>
#include <string>

DistributedField::DistributedField(std::string fieldName,
                                   const DomainConf &domainConf,
                                   size_t npatches)
    // TODO remove domain from here, it does not make sense and is not used
    : fieldName_(fieldName), domain_(domainConf), npatches_(npatches) {}

void DistributedField::insertPatch(SinglePatch &&patch) {
  patches_.push_back(std::move(patch));
}

void DistributedField::insertPatch(SinglePatch &patch) {
  patches_.push_back(patch);
}

void DistributedField::gatherField(field3d &fullfield) {
  std::cout << "Size [" << fullfield.isize() << "," << fullfield.jsize() << ","
            << fullfield.ksize() << "]" << std::endl;
  int cnt = 0;
  for (auto &patch : patches_) {
    std::cout << "IN PATCH " << cnt << " -> [" << patch.lonlen() << ","
              << patch.latlen() << "]" << patch(1, 1) << " ------ "
              << patch.ilonStart() << "," << patch.jlatStart() << std::endl;
    for (int j = 0; j < patch.latlen(); ++j) {
      for (int i = 0; i < patch.lonlen(); ++i) {
        fullfield(i + patch.ilonStart(), j + patch.jlatStart(), patch.lev()) =
            patch(i, j);
      }
    }
    std::cout << "FFFF " << fullfield(60, 30, 0) << " " << fullfield(0, 0, 0)
              << std::endl;
    cnt++;
  }
  std::cout << "OUT " << std::endl;
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

size_t DistributedField::levlen() const { return domain_.levels; }

size_t DistributedField::totlonlen() const { return domain_.isize; }

size_t DistributedField::totlatlen() const { return domain_.jsize; }
