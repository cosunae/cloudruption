import unittest
import fieldop
#import testfieldop
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

        backarr = np.array(field, copy= False)
        self.assertEqual(backarr.shape, (2,4))
        self.assertAlmostEqual(backarr[0][0], 0.0, 6)
        self.assertAlmostEqual(backarr[0][1], 1.2, 6)
        self.assertAlmostEqual(backarr[1][0], 10.11, 6)
        self.assertAlmostEqual(backarr[1][3], 13.0, 6)

    def test_field3d(self):
        arr= np.array( [ [ [0.0,0.1] ], [[10.11,10.12]], [[20.11,20.12]]]).astype(np.float32)

        field = fieldop.field3d(arr)

        self.assertEqual(arr.shape, (3,1,2))
        self.assertAlmostEqual(arr[0][0][0], 0.0, 5)
        self.assertAlmostEqual(arr[0][0][1], 0.1, 5)
        self.assertAlmostEqual(arr[1][0][0], 10.11, 5)
        self.assertAlmostEqual(arr[1][0][1], 10.12, 5)
        self.assertAlmostEqual(arr[2][0][0], 20.11, 5)
        self.assertAlmostEqual(arr[2][0][1], 20.12, 5)

        backarr = np.array(field, copy=False)

        self.assertEqual(backarr.shape, (3,1,2))
        self.assertAlmostEqual(backarr[0][0][0], 0.0, 5)
        self.assertAlmostEqual(backarr[0][0][1], 0.1, 5)
        self.assertAlmostEqual(backarr[1][0][0], 10.11, 5)
        self.assertAlmostEqual(backarr[1][0][1], 10.12, 5)
        self.assertAlmostEqual(backarr[2][0][0], 20.11, 5)
        self.assertAlmostEqual(backarr[2][0][1], 20.12, 5)

#    def test_field3d_cppcomp(self):
#        arr = np.zeros((2,3,4), dtype=np.float32)
#        field = fieldop.field3d(arr)
#        tf = testfieldop.TestFieldOp(field)
#        tf.compute()



    def test_singlepatch(self):
        arr= np.array([[0.0,1.2,2,3],[10.11,11,12,13]]).astype(np.float32)

        field = fieldop.SinglePatch(4,3,2,4,1, arr)

        self.assertAlmostEqual(field[0,0], 0.0, 6)
        self.assertAlmostEqual(field[0,1], 1.2, 6)
        self.assertAlmostEqual(field[1,0], 10.11, 6)
        self.assertAlmostEqual(field[1,3], 13.0, 6)


    def test_bbox(self):
        arr1= np.array([[1.0,1.1,1.2,1.3],[2.0,2.1,2.2,2.3]]).astype(np.float32)
        arr2= np.array([[3.0,3.1,3.2,3.3],[4.0,4.1,4.2,4.3]]).astype(np.float32)

        field1 = fieldop.SinglePatch(0,0,2,4,0, arr1)
        field2 = fieldop.SinglePatch(2,0,2,4,0, arr2)

        domain = fieldop.DomainConf(4,4,1)
        dfield = fieldop.DistributedField("u", domain, 2)

        dfield.insertPatch(field1)
        dfield.insertPatch(field2)

        bbox = dfield.bboxPatches()

        print(bbox.limits_)

    def test_gatherField(self):
        arr1= np.array([[1.0,1.1,1.2,1.3],[2.0,2.1,2.2,2.3]]).astype(np.float32)
        arr2= np.array([[3.0,3.1,3.2,3.3],[4.0,4.1,4.2,4.3]]).astype(np.float32)

        field1 = fieldop.SinglePatch(0,0,2,4,0, arr1)
        field2 = fieldop.SinglePatch(2,0,2,4,0, arr2)

        domain = fieldop.DomainConf(4,4,1)
        dfield = fieldop.DistributedField("u", domain, 2)

        dfield.insertPatch(field1)
        dfield.insertPatch(field2)

        garr = np.empty([4, 4, 1], dtype=np.float32)
        gfield = fieldop.field3d(garr)
        dfield.gatherField(gfield)

        sol = np.array([[[1.0],[1.1],[1.2],[1.3]],[[2.0],[2.1],[2.2],[2.3]],[[3.0],[3.1],[3.2],[3.3]],[[4.0],[4.1],[4.2],[4.3]]]).astype(np.float32)
        self.assertTrue(np.allclose(sol, garr, rtol=1e-5))

if __name__ == '__main__':
    unittest.main()
