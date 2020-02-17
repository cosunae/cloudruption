import unittest

import numpy as np
import parseGrib
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


if __name__ == '__main__':
    unittest.main()
