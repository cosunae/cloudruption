import unittest
import portion as P
import domain_intervals as di
import numpy as np


class TestDomainIntervals(unittest.TestCase):

    def test_getinsertionindex1(self):

        #
        #  Testing insertion in the position marked with x
        #   ____
        #  |    |
        #  |____|
        #   ____      ____
        #  |    |    | x  |
        #  |____|    |__x_|
        #   ____      ____
        #  |    |    |    |
        #  |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(2, 4)), None],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(4, 6)), None]
                                   ])

        self.assertEqual(domain.getInsertionIndex(
            di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))), ((1, False), (1, False)))

    def test_getinsertionindex2(self):

        #
        #  Testing insertion in the position marked with x
        #   ____              ____
        #  |    |            | x  |
        #  |____|            |__x_|
        #   ____
        #  |    |
        #  |____|
        #   ____      ____
        #  |    |    |    |
        #  |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(2, 4)), None],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(4, 6)), None]
                                   ])

        self.assertEqual(domain.getInsertionIndex(
            di.KInterval(P.closedopen(4, 6), P.closedopen(4, 6))), ((2, False), (2, False)))

    def test_getinsertionindex3(self):

        #
        #  Testing insertion in the position marked with x
        #                           ____
        #                          | x  |
        #                          |__x_|
        #
        #
        #   ____
        #  |    |
        #  |____|
        #   ____
        #  |    |
        #  |____|
        #   ____      ____
        #  |    |    |    |
        #  |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(2, 4)), None],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(4, 6)), None]
                                   ])

        self.assertEqual(domain.getInsertionIndex(
            di.KInterval(P.closedopen(6, 8), P.closedopen(8, 10))), ((3, False), (2, False)))

    def test_getinsertionindex4(self):

        #
        #  Testing insertion in the position marked with x
        #               ____
        #              |    |
        #              |____|
        #               ____
        #              |    |
        #              |____|
        #      ____     ____      ____
        #     | x  |   |    |    |    |
        #     |__x_|   |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2)), di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(2, 4),
                                                 P.closedopen(2, 4)), None],
                                   [di.KInterval(P.closedopen(2, 4),
                                                 P.closedopen(4, 6)), None]
                                   ])

        self.assertEqual(domain.getInsertionIndex(
            di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2))), ((0, False), (0, True)))

    def test_getinsertionindex5(self):

        #
        #  Testing insertion in the position marked with x
        #               ____
        #              |    |
        #              |____|
        #               ____
        #              |    |
        #              |____|
        #               ____     ____      ____
        #              |    |   | x  |    |    |
        #              |__ _|   |__x_|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(2, 4)), None],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(4, 6)), None]
                                   ])

        self.assertEqual(domain.getInsertionIndex(
            di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2))), ((0, False), (1, True)))

    def test_getinsertionindex6(self):

        #
        #  Testing insertion in the position marked with x
        #  It will insert where there is already an element with different interval in X,
        #  having to move the pre-existing element in the X direction
        #
        #
        #
        #   ____      ____
        #  |    |    | x  |
        #  |____|    |__x_|
        #   ____      ____
        #  |    |    |    |
        #  |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(2, 4)), di.KInterval(P.closedopen(4, 6), P.closedopen(2, 4))]
                                   ])

        self.assertEqual(domain.getInsertionIndex(
            di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))), ((1, False), (1, True)))

    def test_getinsertionindex7(self):

        #
        #  Testing insertion in the position marked with x
        #  It will insert where there is already an element with the different interval in X,Y,
        #  having to move the pre-existing element in the X,Y direction
        #
        #
        #
        #   ____      ____
        #  |    |    | x  |
        #  |____|    |__x_|
        #   ____      ____
        #  |    |    |    |
        #  |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(4, 6)), di.KInterval(P.closedopen(4, 6), P.closedopen(4, 6))]
                                   ])

        self.assertEqual(domain.getInsertionIndex(
            di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))), ((1, True), (1, True)))

    def test_getinsertionindex8(self):

        #
        #  Testing insertion in the position marked with x
        #  It will try to insert where there is already an element with the same interval in X,
        #
        #
        #
        #   ____      ____
        #  |    |    | x  |
        #  |____|    |__x_|
        #   ____      ____
        #  |    |    |    |
        #  |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 3), P.closedopen(0, 2)), di.KInterval(P.closedopen(2, 4), P.closedopen(0, 4))],
                                   [di.KInterval(P.closedopen(0, 3),
                                                 P.closedopen(2, 4)), di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))]
                                   ])

        self.assertRaises(RuntimeError, domain.getInsertionIndex,
                          di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4)))

    def test_insert1(self):

        #
        #  Testing insertion in the position marked with x
        #   ____
        #  |    |
        #  |____|
        #   ____      ____
        #  |    |    | x  |
        #  |____|    |__x_|
        #   ____      ____
        #  |    |    |    |
        #  |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(2, 4)), None],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(4, 6)), None]
                                   ])
        kinterval = di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))
        position = domain.getInsertionIndex(kinterval)
        domain.insertIntervalImpl(position, kinterval)

        ref = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2))],
                        [di.KInterval(P.closedopen(0, 2),
                                      P.closedopen(2, 4)), di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))],
                        [di.KInterval(P.closedopen(0, 2),
                                      P.closedopen(4, 6)), None]])

        self.assertTrue(np.array_equal(ref, domain.domain_))

    def test_insert2(self):

        #
        #  Testing insertion in the position marked with x
        #               ____
        #              |    |
        #              |____|
        #               ____
        #              |    |
        #              |____|
        #      ____     ____      ____
        #     | x  |   |    |    |    |
        #     |__x_|   |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2)), di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(2, 4),
                                                 P.closedopen(2, 4)), None],
                                   [di.KInterval(P.closedopen(2, 4),
                                                 P.closedopen(4, 6)), None]
                                   ])

        kinterval = di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2))
        position = domain.getInsertionIndex(kinterval)
        domain.insertIntervalImpl(position, kinterval)

        ref = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)),  di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2)),
                         di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
                        [None, di.KInterval(P.closedopen(2, 4),
                                            P.closedopen(2, 4)), None],
                        [None, di.KInterval(P.closedopen(2, 4),
                                            P.closedopen(4, 6)), None]
                        ])

        self.assertTrue(np.array_equal(ref, domain.domain_))

    def test_insert3(self):

        #
        #  Testing insertion in the position marked with x
        #  It will insert where there is already an element with the different interval in X,Y,
        #  having to move the pre-existing element in the X,Y direction
        #
        #
        #
        #   ____      ____
        #  |    |    | x  |
        #  |____|    |__x_|
        #   ____      ____
        #  |    |    |    |
        #  |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2),
                                                 P.closedopen(4, 6)), di.KInterval(P.closedopen(4, 6), P.closedopen(4, 6))]
                                   ])

        kinterval = di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))
        position = domain.getInsertionIndex(kinterval)

        domain.insertIntervalImpl(position, kinterval)

        ref = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)),  None, di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
                        [None, di.KInterval(
                            P.closedopen(2, 4), P.closedopen(2, 4)), None],
                        [di.KInterval(P.closedopen(0, 2),
                                      P.closedopen(4, 6)), None, di.KInterval(P.closedopen(4, 6),
                                                                              P.closedopen(4, 6))]
                        ])

        self.assertTrue(np.array_equal(ref, domain.domain_))

    def test_insert4(self):

        #
        #  Testing insertion in the position marked with x
        #
        #
        #
        #   ____      ____
        #  |    |    | x  |
        #  |____|    |__x_|
        #   ____
        #  |    |
        #  |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2))],
                                   [di.KInterval(P.closedopen(0, 2), P.closedopen(2, 4))]])

        kinterval = di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))
        position = domain.getInsertionIndex(kinterval)
        domain.insertIntervalImpl(position, kinterval)

        ref = np.array([[di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), None],
                        [di.KInterval(P.closedopen(0, 2), P.closedopen(2, 4)), di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))]])

        self.assertTrue(np.array_equal(ref, domain.domain_))

    def test_insert_onempty(self):

        domain = di.domain_intervals()
        domain.domain_ = np.array([[]])

        kinterval = di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))
        position = domain.getInsertionIndex(kinterval)

        domain.insertIntervalImpl(position, kinterval)

        ref = np.array(
            [[di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))]])

        self.assertTrue(np.array_equal(ref, domain.domain_))

    def test_findinterval1(self):

        #
        #  Testing finding the interval with the x
        #               ____
        #              |    |
        #              |____|
        #               ____
        #              |    |
        #              |____|
        #      ____     ____      ____
        #     | x  |   |    |    |    |
        #     |__x_|   |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([
            [di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)),
             di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2)), di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
            [None, di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4)), None],
            [None, di.KInterval(P.closedopen(2, 4), P.closedopen(4, 6)), None]
        ])

        self.assertEqual(domain.findInterval(di.KInterval(
            P.closedopen(2, 4), P.closedopen(4, 6))), (2, 1))

        self.assertEqual(domain.findInterval(di.KInterval(
            P.closedopen(0, 2), P.closedopen(4, 6))), None)
        self.assertEqual(domain.findInterval(di.KInterval(
            P.closedopen(0, 2), P.closedopen(0, 2))), (0, 0))
        self.assertEqual(domain.findInterval(di.KInterval(
            P.closedopen(4, 6), P.closedopen(0, 2))), (0, 2))

    def test_contiguous1(self):

        #
        #  Testing the interval with the x
        #               ____
        #              |    |
        #              |____|
        #               ____
        #              |    |
        #              |____|
        #      ____     ____      ____
        #     |    |   |    |    |    |
        #     |__ _|   |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([
            [di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)), di.KInterval(
                P.closedopen(2, 4), P.closedopen(0, 2)), di.KInterval(P.closedopen(4, 6), P.closedopen(0, 2))],
            [None, di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4)), None],
            [None, di.KInterval(P.closedopen(2, 4), P.closedopen(4, 6)), None]
        ])

        self.assertTrue(not domain.contiguous())

    def test_contiguous2(self):

        #
        #  Testing the interval with the x
        #    ____      ____
        #   |    |    |    |
        #   |____|    |____|
        #    ____      ____
        #   |    |    |    |
        #   |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([
            [di.KInterval(P.closedopen(0, 2), P.closedopen(0, 2)),
             di.KInterval(P.closedopen(2, 4), P.closedopen(0, 2))],
            [di.KInterval(P.closedopen(0, 2), P.closedopen(2, 4)),
             di.KInterval(P.closedopen(2, 4), P.closedopen(2, 4))]
        ])

        self.assertTrue(domain.contiguous())

    def test_enclosure(self):

        #
        #  Testing the enclosure
        #    ____      ____
        #   |    |    |    |
        #   |____|    |____|
        #    ____      ____
        #   |    |    |    |
        #   |____|    |____|

        domain = di.domain_intervals()
        domain.domain_ = np.array([
            [di.KInterval(P.closedopen(0, 6), P.closedopen(3, 5)),
             di.KInterval(P.closedopen(6, 10), P.closedopen(3, 5))],
            [di.KInterval(P.closedopen(0, 6), P.closedopen(3, 5)),
             di.KInterval(P.closedopen(6, 10), P.closedopen(3, 5))]
        ])

        self.assertEqual(domain.enclosure(), di.KInterval(
            P.closedopen(0, 10), P.closedopen(3, 5)))


if __name__ == '__main__':
    unittest.main()
