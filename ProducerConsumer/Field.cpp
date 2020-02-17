#include "Field.h"
#include "Grid.h"

FieldDesc makeGlobalFieldProp(GridConf const &gridconf) {
  return FieldDesc{
      std::vector<size_t>{1, gridconf.lonlen,
                          gridconf.lonlen * gridconf.latlen},
      std::vector<size_t>{gridconf.lonlen, gridconf.latlen, gridconf.levlen}};
}

FieldDesc makeDomainFieldProp(DomainConf const &domain) {
  return FieldDesc{
      std::vector<size_t>{1, domain.isize, domain.isize * domain.jsize},
      std::vector<size_t>{domain.isize, domain.jsize, domain.levels}};
}

FieldProp makeDomainField(std::string variableName, DomainConf const &domain) {
  return FieldProp(variableName, makeDomainFieldProp(domain));
}

FieldDesc makePatchFieldProp(GridConf const &gridconf) {
  return FieldDesc{
      std::vector<size_t>{1, gridconf.isizepatch,
                          gridconf.isizepatch * gridconf.jsizepatch},
      std::vector<size_t>{gridconf.isizepatch, gridconf.jsizepatch,
                          gridconf.levlen}};
}
