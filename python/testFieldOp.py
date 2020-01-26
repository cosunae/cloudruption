import unittest
import fieldop
import numpy as np
import matplotlib.pyplot as plt

class TestFieldOp(unittest.TestCase):

    def test_field2d(self):
        arr= np.array([[0.0,1.2,2,3],[10.11,11,12,13]]).astype(np.float32)

        field = fieldop.field2d(arr)

        self.assertEqual(arr.shape, (2,4))
        self.assertAlmostEqual(arr[0][0], 0.0, 6)
        self.assertAlmostEqual(arr[0][1], 1.2, 6)
        self.assertAlmostEqual(arr[1][0], 10.11, 6)
        self.assertAlmostEqual(arr[1][3], 13.0, 6)

        self.assertAlmostEqual(field[0,0], 0.0, 6)
        self.assertAlmostEqual(field[0,1], 1.2, 6)
        self.assertAlmostEqual(field[1,0], 10.11, 6)
        self.assertAlmostEqual(field[1,3], 13.0, 6)

    def test_singlepatch(self):
        arr= np.array([[0.0,1.2,2,3],[10.11,11,12,13]]).astype(np.float32)

        field = fieldop.SinglePatch(4,3,2,4,1, arr)

        self.assertAlmostEqual(field[0,0], 0.0, 6)
        self.assertAlmostEqual(field[0,1], 1.2, 6)
        self.assertAlmostEqual(field[1,0], 10.11, 6)
        self.assertAlmostEqual(field[1,3], 13.0, 6)

    def test_gatherField(self):
        arr1= np.array([[1.0,1.1,1.2,1.3],[2.0,2.1,2.2,2.3]]).astype(np.float32)
        arr2= np.array([[3.0,3.1,3.2,3.3],[4.0,4.1,4.2,4.3]]).astype(np.float32)

        field1 = fieldop.SinglePatch(0,0,2,4,0, arr1)
        field2 = fieldop.SinglePatch(2,0,2,4,0, arr2)

        domain = fieldop.DomainConf(1,1,4,4,1,0,0)
        dfield = fieldop.DistributedField("u", domain, 2)

        dfield.insertPatch(field1)
        dfield.insertPatch(field2)

        garr = np.empty([4, 4, 1], dtype=np.float32)
        gfield = fieldop.field3d(garr)
        dfield.gatherField(gfield, 4*4*1)

        sol = np.array([[[1.0],[1.1],[1.2],[1.3]],[[2.0],[2.1],[2.2],[2.3]],[[3.0],[3.1],[3.2],[3.3]],[[4.0],[4.1],[4.2],[4.3]]]).astype(np.float32)
        self.assertTrue(np.allclose(sol, garr, rtol=1e-5))

if __name__ == '__main__':
    unittest.main()
