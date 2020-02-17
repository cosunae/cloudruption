#include "Field.h"
#include "Grid.h"

FieldProp makeGlobalFieldProp(GridConf const &gridconf) {
  return FieldProp{
      std::vector<size_t>{1, gridconf.lonlen,
                          gridconf.lonlen * gridconf.latlen},
      std::vector<size_t>{gridconf.lonlen, gridconf.latlen, gridconf.levlen}};
}

FieldProp makeDomainFieldProp(DomainConf const &domain) {
  return FieldProp{
      std::vector<size_t>{1, domain.isize, domain.isize * domain.jsize},
      std::vector<size_t>{domain.isize, domain.jsize, domain.levels}};
}

Field makeDomainField(std::string variableName, DomainConf const &domain) {
  return Field(variableName, makeDomainFieldProp(domain));
}

FieldProp makePatchFieldProp(GridConf const &gridconf) {
  return FieldProp{
      std::vector<size_t>{1, gridconf.isizepatch,
                          gridconf.isizepatch * gridconf.jsizepatch},
      std::vector<size_t>{gridconf.isizepatch, gridconf.jsizepatch,
                          gridconf.levlen}};
}
