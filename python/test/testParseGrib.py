import unittest

import numpy as np
#import parseGrib
import parseGrib as grib


class TestParseGrib(unittest.TestCase):
    def test_cosmogrib(self):

        self.assertEqual(grib.gribParams["U"], {'table': 2, 'parameter': 33})
        self.assertEqual(grib.gribParams["PS"], {
            "table": 2,
            "parameter": 1,
            "typeLevel": 1,
        })

    def test_cosmotypelevel(self):

        self.assertEqual(grib.typeLevelParams["surface"], 1)
        self.assertEqual(grib.typeLevelParams["meanSea"], 102)

    def test_getfield(self):
        self.assertEqual(grib.getGribFieldname(table2Version=244, indicatorOfParameter=96,
                                               indicatorOfTypeOfLevel="sfc", typeOfLevel="surface", timeRangeIndicator=0), "ALNUhcem")
        self.assertEqual(grib.getGribFieldname(table2Version=201, indicatorOfParameter=139,
                                               indicatorOfTypeOfLevel="ml", typeOfLevel="hybridLayer", timeRangeIndicator=0), "PP")
        self.assertEqual(grib.getGribFieldname(table2Version=2, indicatorOfParameter=33,
                                               indicatorOfTypeOfLevel="ml", typeOfLevel="hybridLayer", timeRangeIndicator=0), "U")
        self.assertEqual(grib.getGribFieldname(table2Version=2, indicatorOfParameter=51,
                                               indicatorOfTypeOfLevel="ml", typeOfLevel="hybridLayer", timeRangeIndicator=0), "QV")


if __name__ == '__main__':
    unittest.main()
