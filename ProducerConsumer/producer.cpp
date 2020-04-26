#include "Config.h"
#include "KeyMessage.h"
#include "SinglePatch.h"
#include "eccodes.h"
#include <algorithm>
#include <assert.h>
#include <chrono>
#include <iostream>
#include <limits.h>
#include <math.h>
#ifdef ENABLE_MPI
#include <mpi.h>
#endif
#include <filesystem>
#include <iostream>
#include <netcdf.h>
#include <numeric>
#include <set>
#include <stdint.h>
#include <stdio.h>
#include <string>
#include <vector>

#include "FieldProp.h"
#include "Grid.h"
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <filesystem>
#include "KafkaProducer.h"

namespace fs = std::filesystem;

#if SIZE_MAX == UCHAR_MAX
#define MPI_SIZE_T MPI_UNSIGNED_CHAR
#elif SIZE_MAX == USHRT_MAX
#define MPI_SIZE_T MPI_UNSIGNED_SHORT
#elif SIZE_MAX == UINT_MAX
#define MPI_SIZE_T MPI_UNSIGNED
#elif SIZE_MAX == ULONG_MAX
#define MPI_SIZE_T MPI_UNSIGNED_LONG
#elif SIZE_MAX == ULLONG_MAX
#define MPI_SIZE_T MPI_UNSIGNED_LONG_LONG
#else
#error "Unknown TYPE"
#endif

/* Handle errors by printing an error message and exiting with a
 * non-zero status. */
#define ERR(e)                             \
  {                                        \
    printf("Error: %s\n", nc_strerror(e)); \
    return e;                              \
  }
#define ERRC(e)                            \
  {                                        \
    printf("Error: %s\n", nc_strerror(e)); \
    ierror = e;                            \
  }

void mpierror()
{
#ifdef ENABLE_MPI
  MPI_Abort(MPI_COMM_WORLD, -1);
#else
  throw std::runtime_error("mpi error");
#endif
}

long getTimestamp(codes_handle *h)
{
  long year, month, day, hour, minute, second;
  CODES_CHECK(codes_get_long(h, "year", &year), 0);
  CODES_CHECK(codes_get_long(h, "month", &month), 0);
  CODES_CHECK(codes_get_long(h, "day", &day), 0);
  CODES_CHECK(codes_get_long(h, "hour", &hour), 0);
  CODES_CHECK(codes_get_long(h, "minute", &minute), 0);
  CODES_CHECK(codes_get_long(h, "second", &second), 0);

  std::tm c = {(int)second, (int)minute, (int)hour, (int)day, (int)month,
               (int)year, 0, 0, -1};

  std::time_t l = std::mktime(&c);
  return static_cast<long>(l);
}

struct FieldMetadata
{
  long longitudeOfFirstGridPoint, longitudeOfLastGridPoint,
      latitudeOfFirstGridPoint, latitudeOfLastGridPoint;
};

class FieldHandler
{
  const int mpirank_, mpisize_;
  std::string filename_;
  long timestamp_;
  std::string parseGribExe_;

  GridConf gridconf_;
  SubDomainConf subdomainconf_;
  std::optional<FieldDesc> globalFieldProp_;
  std::optional<FieldDesc> domainFieldProp_;
  std::optional<FieldDesc> patchFieldProp_;
  std::unordered_map<std::string, FieldMetadata> allFields_;
  std::unordered_map<std::string, size_t> levels_;
  std::unordered_map<std::string, std::vector<int>> topLevels_;
  size_t numMessages_;

  std::unordered_map<std::string, field3d *> fglob_;
  field3d *fsubd_ = nullptr;

public:
  FieldHandler(int mpirank, int mpisize, std::string filename, long timestamp,
               std::string parseGribExe)
      : mpirank_(mpirank), mpisize_(mpisize), filename_(filename),
        timestamp_(timestamp), parseGribExe_(parseGribExe)
  {
    // domain decomposition as
    // 0 1 2
    // 3 4 5

    float a = std::sqrt(mpisize_);
    for (int i = (int)a; i > 0; --i)
    {
      if (mpisize_ % i == 0)
      {
        gridconf_.nbx = i;
        gridconf_.nby = mpisize_ / gridconf_.nbx;
        break;
      }
    }

    if (gridconf_.nbx == -1 || gridconf_.nby == -1)
    {
      throw std::runtime_error(
          "Error: could not find a valid domain decomposition");
    }
  }

  void setupGlobalField(std::string fieldname)
  {
    if (mpirank_ != 0)
      throw std::runtime_error("global field can only be setup by mpirank 0");

    if (!fglob_.count(fieldname))
    {
      fglob_[fieldname] =
          new field3d(gridconf_.lonlen, gridconf_.latlen, gridconf_.levlen);
    }
  }

  int setupGridConf()
  {

    subdomainconf_.levels = gridconf_.levlen;

    size_t nx = mpirank_ % gridconf_.nbx;
    size_t ny = mpirank_ / gridconf_.nbx;

    gridconf_.isizepatch =
        (gridconf_.lonlen + gridconf_.nbx - 1) / gridconf_.nbx;
    subdomainconf_.istart = nx * gridconf_.isizepatch;
    subdomainconf_.isize = std::min(gridconf_.isizepatch,
                                    gridconf_.lonlen - subdomainconf_.istart);

    gridconf_.jsizepatch =
        (gridconf_.latlen + gridconf_.nby - 1) / gridconf_.nby;
    subdomainconf_.jstart = ny * gridconf_.jsizepatch;
    subdomainconf_.jsize = std::min(gridconf_.jsizepatch,
                                    gridconf_.latlen - subdomainconf_.jstart);

    globalFieldProp_ = makeGlobalFieldProp(gridconf_);
    domainFieldProp_ = makeDomainFieldProp(subdomainconf_);
    patchFieldProp_ = makePatchFieldProp(gridconf_);

    return 0;
  }

  int getMpiRank() const { return mpirank_; }
  int getMpiSize() const { return mpisize_; }
  FieldDesc getGlobalFieldProp() const { return globalFieldProp_.value(); }
  FieldDesc getDomainFieldProp() const { return domainFieldProp_.value(); }
  const SubDomainConf &getSubdomainconf() const { return subdomainconf_; }
  const GridConf &getGridconf() const { return gridconf_; }

  field3d &getSubdomainField() const
  {
    assert(fsubd_);
    return *fsubd_;
  }

  void printConf()
  {
    if (mpirank_ == 0)
    {
      std::cout << "------------  domain conf ------------" << std::endl;
      std::cout << "nbx : " << gridconf_.nbx << std::endl;
      std::cout << "nby : " << gridconf_.nby << std::endl;

      gridconf_.print();
    }
  }

  std::string getFieldName(long table2Version, long indicatorOfParameter,
                           std::string indicatorOfTypeOfLevel, long typeOfLevel,
                           long timeRangeIndicator)
  {

    PyObject *pName, *pModule, *pFunc;
    PyObject *pArgs, *pValue;

    Py_Initialize();

    std::string moduleName =
        fs::path(fs::path(parseGribExe_).replace_extension("")).filename();
    std::string modulePath = fs::path(parseGribExe_).parent_path();

    PyObject *sys = PyImport_ImportModule("sys");
    PyObject *path = PyObject_GetAttrString(sys, "path");
    PyList_Append(path, PyUnicode_FromString(modulePath.c_str()));

    pName = PyUnicode_DecodeFSDefault(moduleName.c_str());
    /* Error checking of pName left out */

    pModule = PyImport_Import(pName);
    Py_DECREF(pName);
    if (!pModule)
    {
      PyErr_Print();
      throw std::runtime_error("Failed to load");
    }

    pFunc = PyObject_GetAttrString(pModule, "getGribFieldname_c");
    /* pFunc is a new reference */

    if (!pFunc || !PyCallable_Check(pFunc))
    {
      if (PyErr_Occurred())
        PyErr_Print();
      throw std::runtime_error("Call Failed");
    }

    pArgs = PyTuple_New(5);
    pValue = PyLong_FromLong(table2Version);
    if (!pValue)
    {
      Py_DECREF(pArgs);
      Py_DECREF(pModule);
      throw std::runtime_error("Cannot convert argument\n");
    }
    /* pValue reference stolen here: */
    PyTuple_SetItem(pArgs, 0, pValue);

    pValue = PyLong_FromLong(indicatorOfParameter);
    if (!pValue)
    {
      Py_DECREF(pArgs);
      Py_DECREF(pModule);
      throw std::runtime_error("Cannot convert argument\n");
    }
    /* pValue reference stolen here: */
    PyTuple_SetItem(pArgs, 1, pValue);

    pValue = PyUnicode_FromString(indicatorOfTypeOfLevel.c_str());
    if (!pValue)
    {
      Py_DECREF(pArgs);
      Py_DECREF(pModule);
      throw std::runtime_error("Cannot convert argument\n");
    }
    /* pValue reference stolen here: */
    PyTuple_SetItem(pArgs, 2, pValue);

    pValue = PyLong_FromLong(typeOfLevel);
    if (!pValue)
    {
      Py_DECREF(pArgs);
      Py_DECREF(pModule);
      throw std::runtime_error("Cannot convert argument\n");
    }
    /* pValue reference stolen here: */
    PyTuple_SetItem(pArgs, 3, pValue);

    pValue = PyLong_FromLong(timeRangeIndicator);
    if (!pValue)
    {
      Py_DECREF(pArgs);
      Py_DECREF(pModule);
      throw std::runtime_error("Cannot convert argument\n");
    }
    /* pValue reference stolen here: */
    PyTuple_SetItem(pArgs, 4, pValue);

    pValue = PyObject_CallObject(pFunc, pArgs);
    if (!pValue)
    {
      if (PyErr_Occurred())
        PyErr_Print();
      throw std::runtime_error("Error capturing python result");
    }
    std::string res = PyUnicode_AsUTF8(pValue);
    Py_DECREF(pValue);
    Py_XDECREF(pFunc);
    Py_DECREF(pModule);

    if (Py_FinalizeEx() < 0)
    {
      throw std::runtime_error("Error closing python interpreter");
    }

    return res;
  }
  void getFileMetadata()
  {
    FILE *in = NULL;
    int err = 0;

    /* Message handle. Required in all the ecCodes calls acting on a
     * message.*/
    codes_handle *h = NULL;
    if (mpirank_ == 0)
    {

      in = fopen(filename_.c_str(), "rb");
      if (!in)
      {
        printf("ERROR: unable to open file %s\n", filename_.c_str());
        exit(1);
      }

      // We are looping two times over the metadata in order to first get
      // the number of levels of each field that should be used for every
      // msg of the second loop that sends data to kafka
      /* Loop on all the messages in a file.*/
      while ((h = codes_handle_new_from_file(0, in, PRODUCT_GRIB, &err)) !=
             NULL)
      {
        /* Check of errors after reading a message. */
        if (err != CODES_SUCCESS)
          CODES_CHECK(err, 0);

        if (timestamp_ != getTimestamp(h))
          continue;

        long ni, nj, table2Version, indicatorOfParameter, timeRangeIndicator;
        CODES_CHECK(codes_get_long(h, "Ni", &ni), 0);
        CODES_CHECK(codes_get_long(h, "Nj", &nj), 0);
        CODES_CHECK(codes_get_long(h, "table2Version", &table2Version), 0);
        CODES_CHECK(
            codes_get_long(h, "indicatorOfParameter", &indicatorOfParameter),
            0);
        char indicatorOfTypeOfLevel[256];
        size_t msgsize = 256;

        CODES_CHECK(codes_get_string(h, "indicatorOfTypeOfLevel",
                                     indicatorOfTypeOfLevel, &msgsize),
                    0);

        long typeOfLevel;
        CODES_CHECK(codes_get_long(h, "typeOfLevel", &typeOfLevel), 0);

        CODES_CHECK(
            codes_get_long(h, "timeRangeIndicator", &timeRangeIndicator), 0);

        std::string fieldname =
            getFieldName(table2Version, indicatorOfParameter,
                         std::string(indicatorOfTypeOfLevel), typeOfLevel,
                         timeRangeIndicator);

        if (fieldname == "None")
          continue;

        FieldMetadata fmetadata;
        CODES_CHECK(codes_get_long(h, "longitudeOfFirstGridPoint",
                                   &fmetadata.longitudeOfFirstGridPoint),
                    0);
        CODES_CHECK(codes_get_long(h, "longitudeOfLastGridPoint",
                                   &fmetadata.longitudeOfLastGridPoint),
                    0);
        CODES_CHECK(codes_get_long(h, "latitudeOfFirstGridPoint",
                                   &fmetadata.latitudeOfFirstGridPoint),
                    0);
        CODES_CHECK(codes_get_long(h, "latitudeOfLastGridPoint",
                                   &fmetadata.latitudeOfLastGridPoint),
                    0);

        allFields_[fieldname] = fmetadata;

        if (levels_.count(fieldname))
        {
          levels_[fieldname] = levels_[fieldname] + 1;
        }
        else
        {
          levels_[fieldname] = 1;
        }
        long bottomLevel;
        CODES_CHECK(codes_get_long(h, "bottomLevel", &bottomLevel), 0);
        long topLevel;
        CODES_CHECK(codes_get_long(h, "topLevel", &topLevel), 0);

        if (!topLevels_.count(fieldname))
        {
          topLevels_[fieldname] = std::vector<int>();
          topLevels_[fieldname].push_back(topLevel);
        }
        else
        {
          auto &levelsList = topLevels_[fieldname];
          topLevels_[fieldname].insert(
              std::lower_bound(levelsList.begin(), levelsList.end(), topLevel),
              topLevel);
        }
        /* At the end the codes_handle is deleted to free memory. */
        codes_handle_delete(h);
      }
      fclose(in);
    }

    const int maxfieldnamesize = 32;
    int numFields = allFields_.size();

#ifdef ENABLE_MPI
    MPI_Bcast(&numFields, 1, MPI_INT, 0, MPI_COMM_WORLD);
#endif

    size_t allfields_buffersize = maxfieldnamesize * numFields;

#ifdef ENABLE_MPI
    MPI_Bcast(&allfields_buffersize, 1, MPI_INT, 0, MPI_COMM_WORLD);
#endif
    char fbuff[allfields_buffersize];

    std::vector<int> fieldnamesizes(numFields);
    if (mpirank_ == 0)
    {
      int i = 0;
      for (auto &field : allFields_)
      {
        strcpy(&(fbuff[32 * i]), field.first.c_str());
        fieldnamesizes[i] = field.first.size();
        ++i;
      }
    }

#ifdef ENABLE_MPI
    MPI_Bcast(fieldnamesizes.data(), numFields, MPI_INT, 0, MPI_COMM_WORLD);

    MPI_Bcast(&fbuff, allfields_buffersize, MPI_CHAR, 0, MPI_COMM_WORLD);
#endif
    std::vector<FieldMetadata> lmetadata(numFields);
    if (mpirank_ == 0)
    {
      int i = 0;
      for (auto &field : allFields_)
      {
        lmetadata[i] = field.second;
        ++i;
      }
    }
#ifdef ENABLE_MPI
    MPI_Bcast(lmetadata.data(), numFields * 4, MPI_LONG, 0, MPI_COMM_WORLD);
#endif
    if (mpirank_ != 0)
    {
      for (int i = 0; i < numFields; ++i)
      {
        std::stringstream ss;
        for (int j = 32 * i; j < 32 * i + fieldnamesizes[i]; ++j)
          ss << fbuff[j];
        std::string fieldname;
        ss >> fieldname;
        FieldMetadata fmetadata = lmetadata[i];
        allFields_[fieldname] = fmetadata;
      }
    }
    else
    {
      for (int i = 0; i < numFields; ++i)
      {

        std::stringstream ss;
        for (int j = 32 * i; j < 32 * i + fieldnamesizes[i]; ++j)
          ss << fbuff[j];
        std::string fieldname;
        ss >> fieldname;
      }
    }

    int levelssize;
    if (mpirank_ == 0)
    {
      levelssize = levels_.size();
    }
#ifdef ENABLE_MPI
    MPI_Bcast(&levelssize, 1, MPI_INT, 0, MPI_COMM_WORLD);
#endif
    std::vector<size_t> levelsflat(levelssize);

    if (mpirank_ == 0)
    {
      int i = 0;
      for (auto &field : allFields_)
      {
        levelsflat[i] = levels_[field.first];
        i++;
      }
    }
#ifdef ENABLE_MPI
    MPI_Bcast(levelsflat.data(), levelssize, MPI_LONG, 0, MPI_COMM_WORLD);
#endif

    if (mpirank_ != 0)
    {
      int i = 0;
      for (auto &field : allFields_)
      {
        levels_[field.first] = levelsflat[i];
        i++;
      }
    }
    numMessages_ = std::accumulate(
        std::next(levels_.begin()), levels_.end(), levels_.begin()->second,
        [](int acc, std::pair<std::string, int> p) { return acc + p.second; });
  }

  void getMessages()
  {

    FILE *in = NULL;
    int err = 0;
    char *filename = NULL;

    /* Message handle. Required in all the ecCodes calls acting on a
     * message.*/
    codes_handle *h = NULL;

    if (mpirank_ == 0)
    {
      in = fopen(filename_.c_str(), "rb");
      if (!in)
      {
        printf("ERROR: unable to open file %s\n", filename);
        exit(1);
      }

      /* Loop on all the messages in a file.*/
      while ((h = codes_handle_new_from_file(0, in, PRODUCT_GRIB, &err)) !=
             NULL)
      {
        /* Check of errors after reading a message. */
        if (err != CODES_SUCCESS)
          CODES_CHECK(err, 0);

        if (timestamp_ != getTimestamp(h))
          continue;

        long ni, nj, table2Version, indicatorOfParameter, timeRangeIndicator;
        CODES_CHECK(codes_get_long(h, "Ni", &ni), 0);
        CODES_CHECK(codes_get_long(h, "Nj", &nj), 0);
        CODES_CHECK(codes_get_long(h, "table2Version", &table2Version), 0);
        CODES_CHECK(
            codes_get_long(h, "indicatorOfParameter", &indicatorOfParameter),
            0);
        char indicatorOfTypeOfLevel[256];
        size_t msgsize = 256;

        CODES_CHECK(codes_get_string(h, "indicatorOfTypeOfLevel",
                                     indicatorOfTypeOfLevel, &msgsize),
                    0);

        long typeOfLevel;
        CODES_CHECK(codes_get_long(h, "typeOfLevel", &typeOfLevel), 0);

        CODES_CHECK(
            codes_get_long(h, "timeRangeIndicator", &timeRangeIndicator), 0);

        std::string fieldname =
            getFieldName(table2Version, indicatorOfParameter,
                         std::string(indicatorOfTypeOfLevel), typeOfLevel,
                         timeRangeIndicator);

        if (fieldname == "None")
          continue;

        gridconf_.lonlen = ni;
        gridconf_.latlen = nj;
        gridconf_.levlen = levels_[fieldname];

        setupGridConf();

        setupGlobalField(fieldname);

        size_t values_len;
        double *values = NULL;

        long topLevel;
        CODES_CHECK(codes_get_long(h, "topLevel", &topLevel), 0);

        long jConsecutive;
        CODES_CHECK(codes_get_long(h, "jPointsAreConsecutive", &jConsecutive),
                    0);

        if (jConsecutive)
        {
          throw std::runtime_error("jpoints consecutive not supported");
        }

        /* get the size of the values array*/
        CODES_CHECK(codes_get_size(h, "values", &values_len), 0);

        field3d *ffield = fglob_[fieldname];
        if (values_len != ffield->isize() * ffield->jsize())
        {
          throw std::runtime_error(
              "values extracted do not match in size with metadata");
        }

        values = (double *)malloc(values_len * sizeof(double));

        auto &levelsList = topLevels_[fieldname];
        int k = std::distance(
            levelsList.begin(),
            std::lower_bound(levelsList.begin(), levelsList.end(), topLevel));

        /* get data values*/
        CODES_CHECK(codes_get_double_array(h, "values", values, &values_len),
                    0);

        for (int i = 0; i < ffield->isize(); ++i)
        {
          for (int j = 0; j < ffield->jsize(); ++j)
          {
            (*ffield)(i, j, k) = values[i + j * ffield->isize()];
          }
        }

        /* At the end the codes_handle is deleted to free memory. */
        codes_handle_delete(h);
      }

      fclose(in);
    }
  }

  void produce(KafkaProducer const &producer)
  {
    for (auto field : allFields_)
    {
      auto fieldname = field.first;
      auto fieldmetadata = field.second;
      if (mpirank_ == 0)
      {
        field3d *ffield = fglob_[fieldname];

        gridconf_.lonlen = ffield->isize();
        gridconf_.latlen = ffield->jsize();
        gridconf_.levlen = levels_[fieldname];
      }
#ifdef ENABLE_MPI
      MPI_Bcast(&gridconf_, sizeof(GridConf) / sizeof(size_t), MPI_SIZE_T, 0,
                MPI_COMM_WORLD);
#endif
      setupGridConf();
      scatterSubdomains(fieldname);

      std::cout << "Producing " << fieldname << std::endl;
      for (size_t k = 0; k < gridconf_.levlen; ++k)
      {
        producer.produce(getMsgKey(ActionType::Data, timestamp_, fieldname,
                                   fieldmetadata, k),
                         (&(getSubdomainField()(0, 0, k))),
                         getDomainFieldProp().getSizes()[0] *
                             getDomainFieldProp().getSizes()[1] * sizeof(float),
                         fieldname);
      }
    }
  }

  void scatterSubdomains(std::string fieldname)
  {
    field3d ft(patchFieldProp_->getSizes()[0], patchFieldProp_->getSizes()[1],
               patchFieldProp_->getSizes()[2]);

    float *fscat = nullptr;
    if (mpirank_ == 0)
    {
      size_t istridet = 1;
      size_t jstridet = istridet * gridconf_.isizepatch;
      size_t kstridet = jstridet * gridconf_.jsizepatch;
      size_t bistridet = kstridet * gridconf_.levlen;
      size_t bjstridet = bistridet * gridconf_.nbx;

      // temporary field to prepare all the blocks
      fscat = (float *)malloc(patchFieldProp_->totalsize_ * gridconf_.nbx *
                              gridconf_.nby * sizeof(float));
      for (int bj = 0; bj < gridconf_.nby; ++bj)
      {
        for (int bi = 0; bi < gridconf_.nbx; ++bi)
        {
          for (int k = 0; k < gridconf_.levlen; ++k)
          {
            for (int j = 0; j < gridconf_.jsizepatch; ++j)
            {
              for (int i = 0; i < gridconf_.isizepatch; ++i)
              {

                size_t iglb = bi * gridconf_.isizepatch + i;
                size_t jglb = bj * gridconf_.jsizepatch + j;
                if (iglb >= gridconf_.lonlen || jglb >= gridconf_.latlen)
                  continue;

                if (i * istridet + j * jstridet + k * kstridet +
                        bi * bistridet + bj * bjstridet >=
                    patchFieldProp_->totalsize_ * gridconf_.nbx *
                        gridconf_.nby * sizeof(float))
                {
                  mpierror();
                  throw std::runtime_error("ERROR out of bound");
                }
                if (iglb * globalFieldProp_->strides_[0] +
                        jglb * globalFieldProp_->strides_[1] +
                        k * globalFieldProp_->strides_[2] >=
                    globalFieldProp_->totalsize_ * sizeof(float))
                {
                  mpierror();
                  throw std::runtime_error("ERROR out of bound");
                }

                fscat[i * istridet + j * jstridet + k * kstridet +
                      bi * bistridet + bj * bjstridet] =
                    (*fglob_[fieldname])(iglb, jglb, (size_t)k);
              }
            }
          }
        }
      }
    }

#ifdef ENABLE_MPI
    MPI_Scatter(fscat,
                gridconf_.isizepatch * gridconf_.jsizepatch * gridconf_.levlen,
                MPI_FLOAT, ft.data(),
                gridconf_.isizepatch * gridconf_.jsizepatch * gridconf_.levlen,
                MPI_FLOAT, 0, MPI_COMM_WORLD);
#endif

    if (mpirank_ == 0)
    {
      free(fscat);
    }
    if (fsubd_)
    {
      free(fsubd_);
    }
    fsubd_ = new field3d(subdomainconf_.isize, subdomainconf_.jsize,
                         subdomainconf_.levels);

    for (size_t k = 0; k < gridconf_.levlen; ++k)
    {
      for (size_t j = 0; j < subdomainconf_.jsize; ++j)
      {
        for (size_t i = 0; i < subdomainconf_.isize; ++i)
        {
#ifdef ENABLE_MPI
          (*fsubd_)(i, j, k) = ft(i, j, k);
#else
          (*fsubd_)(i, j, k) = (*fglob_[fieldname])(i, j, k);
#endif
        }
      }
    }
  }
  KeyMessage getMsgKey(ActionType actionType, size_t timestamp,
                       std::string fieldname, const FieldMetadata &metadata,
                       const size_t lev) const
  {
    const auto &subdomainconf = getSubdomainconf();
    auto domainFieldProp = getDomainFieldProp();
    const auto &gridconf = getGridconf();

    const float dx = 60;

    KeyMessage key{actionType, "", getMpiSize(), getMpiRank(), timestamp,
                   subdomainconf.istart, subdomainconf.jstart, lev,
                   domainFieldProp.sizes_[0], domainFieldProp.sizes_[1],
                   domainFieldProp.sizes_[2], gridconf.lonlen, gridconf.latlen,
                   // emulating staggering
                   (float)metadata.longitudeOfFirstGridPoint,
                   (float)metadata.longitudeOfLastGridPoint,
                   (float)metadata.latitudeOfFirstGridPoint,
                   (float)metadata.latitudeOfLastGridPoint};

    int strlength = std::min(fieldname.size() + 1, (size_t)32);
    fieldname.substr(0, strlength).copy(key.key, strlength);
    key.key[strlength - 1] = '\0';

    return key;
  }
};

class GribDecoder
{
  std::string filename_;
  int mpirank_;
  int mpisize_;

public:
  GribDecoder(int mpirank, int mpisize, std::string filename)
      : filename_(filename), mpirank_(mpirank), mpisize_(mpisize) {}

  void decode(KafkaProducer const &producer, std::string parseGribExe)
  {

    FILE *in = NULL;
    int err = 0;

    std::set<long> timestamps;
    /* Message handle. Required in all the ecCodes calls acting on a
     * message.*/
    codes_handle *h = NULL;
    if (mpirank_ == 0)
    {

      in = fopen(filename_.c_str(), "rb");
      if (!in)
      {
        printf("ERROR: unable to open file %s\n", filename_.c_str());
        exit(1);
      }

      // We are looping two times over the metadata in order to first get
      // the number of levels of each field that should be used for every
      // msg of the second loop that sends data to kafka
      /* Loop on all the messages in a file.*/
      while ((h = codes_handle_new_from_file(0, in, PRODUCT_GRIB, &err)) !=
             NULL)
      {
        /* Check of errors after reading a message. */
        if (err != CODES_SUCCESS)
          CODES_CHECK(err, 0);

        long timestamp = getTimestamp(h);

        if (timestamps.count(timestamp))
          continue;
        else
        {
          timestamps.insert(timestamp);
        }
        /* At the end the codes_handle is deleted to free memory. */
        codes_handle_delete(h);
      }
      fclose(in);
    }

    std::vector<long> vtimestamps;
    std::copy(timestamps.begin(), timestamps.end(),
              std::back_inserter(vtimestamps));

    long timest_size = vtimestamps.size();
#ifdef ENABLE_MPI
    MPI_Bcast(&timest_size, 1, MPI_LONG, 0, MPI_COMM_WORLD);
#endif
    if (mpirank_ != 0)
    {
      vtimestamps.resize(timest_size);
    }
#ifdef ENABLE_MPI
    MPI_Bcast(vtimestamps.data(), timest_size, MPI_LONG, 0, MPI_COMM_WORLD);
#endif
    for (auto timestamp : vtimestamps)
    {
      std::cout << "[" << mpirank_ << "] Processing timestamp :" << timestamp
                << std::endl;
      FieldHandler fhandler(mpirank_, mpisize_, filename_, timestamp,
                            parseGribExe);
      fhandler.getFileMetadata();
      fhandler.getMessages();
      fhandler.produce(producer);
    }
  }
};

int main(int argc, char **argv)
{
#ifdef ENABLE_MPI
  MPI_Init(&argc, &argv);
#endif
  int myrank = 0;
  int mpisize = 1;

  std::string config_filename = "config.json";
  if (argc > 1)
  {
    config_filename = std::string(argv[1]);
  }
  Config config(config_filename);

  if (!std::filesystem::exists(config.get<std::string>("parsegrib")))
  {
    throw std::runtime_error(
        "parseGrib python file defined in config.json does not exists :" +
        config.get<std::string>("parsegrib"));
  }

  if (config.has("lockfile"))
  {
    if (std::filesystem::exists(config.get<std::string>("lockfile")))
    {
      throw std::runtime_error("lock file exists, can not acquire lock");
    }
    std::ofstream f(config.get<std::string>("lockfile"));
    f << "lock";
    f.close();
  }

  auto topics = config.getTopics();
#ifdef ENABLE_MPI
  MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
  MPI_Comm_size(MPI_COMM_WORLD, &mpisize);
#endif
  auto files = config.getFiles();

  for (auto file : files)
  {
    KafkaProducer producer(config.get<std::string>("kafkabroker"));

    GribDecoder gribDecoder(myrank, mpisize, file);
    gribDecoder.decode(producer, config.get<std::string>("parsegrib"));
  }
#ifdef ENABLE_MPI
  MPI_Finalize();
#endif

  if (config.has("lockfile"))
  {
    std::remove(config.get<std::string>("lockfile").c_str());
  }
}
