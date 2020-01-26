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

void DistributedField::gatherField(field3d &fullfield, int totalsize) {
  assert(totalsize == totlonlen() * totlatlen() * levlen());

  for (auto &patch : patches_) {
    for (int j = 0; j < patch.latlen(); ++j) {
      for (int i = 0; i < patch.lonlen(); ++i) {
        fullfield(i + patch.ilonStart(), j + patch.jlatStart(), patch.lev()) =
            patch(i, j);
      }
    }
  }
}

void DistributedField::writeIfComplete(NetCDFDumper &netcdfDumper) {
  if (npatches_ != patches_.size())
    return;

  field3d fullfield(totlonlen(), totlatlen(), levlen());

  gatherField(fullfield, totlonlen() * totlatlen() * levlen());
  netcdfDumper.writeVar(fieldName_, fullfield.data());

  patches_.clear();
}

size_t DistributedField::levlen() const { return domain_.levels; }

size_t DistributedField::totlonlen() const { return domain_.isize; }

size_t DistributedField::totlatlen() const { return domain_.jsize; }
