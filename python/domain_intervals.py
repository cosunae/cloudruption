import portion as P
import numpy as np
from dataclasses import dataclass
import data
import fieldop


@dataclass
class KInterval:
    x_: P.Interval
    y_: P.Interval

    def overlaps(self, other):
        return self.x_.overlaps(other.x_) and self.y_.overlaps(other.y_)

    def __hash__(self):
        return (str(self.x_.upper)+str(self.x_.lower)+str(self.y_.upper) + str(self.y_.lower)).__hash__()


def intervalSize(a: P.Interval):
    return a.upper - a.lower


class domain_intervals:

    def __init__(self):
        self.domain_ = np.array([[]])

    def contiguous(self):
        for j in range(self.domain_.shape[0]):
            for i in range(self.domain_.shape[1]):
                elem = self.domain_[j][i]
                if elem is None:
                    return False
                if i != 0:
                    if not elem.x_.adjacent(self.domain_[j][i-1].x_):
                        return False
                if j != 0:
                    if not elem.y_.adjacent(self.domain_[j-1][i].y_):
                        return False
        return True

    def enclosure(self):
        return KInterval(P.closedopen(self.domain_[0][0].x_.lower, self.domain_[0][self.domain_.shape[1]-1].x_.upper),
                         P.closedopen(self.domain_[0][0].y_.lower, self.domain_[self.domain_.shape[0]-1][0].y_.upper))

    def complete(self, data_desc: fieldop.DataDesc):
        if not self.contiguous():
            return False
        if self.domain_.size == 0:
            return False
        if self.enclosure() == KInterval(P.closedopen(0, data_desc.totlonlen), P.closedopen(0, data_desc.totlatlen)):
            return True
        return False

    def findInterval(self, xyInt: KInterval):
        if self.domain_.size == 0:
            return None
        for index, kint in np.ndenumerate(self.domain_):
            if kint == xyInt:
                return index
        return None

    def overlaps(self, xyInt: KInterval):
        if self.domain_.size == 0:
            return False
        for j in range(self.domain_.shape[0]):
            for i in range(self.domain_.shape[1]):
                kint = self.domain_[j][i]
                if kint is None:
                    continue

        # nditer does not work on a 2d array with one element
        # for kint in np.nditer(self.domain_, ['refs_ok']):
                if kint.overlaps(xyInt):
                    return True
        return False

    def insertInterval(self, xyInt: KInterval):
        self.insertIntervalImpl(self.getInsertionIndex(xyInt), xyInt)

    def insertIntervalImpl(self, pos, xyInt: KInterval):
        if self.domain_.size == 0:
            if pos[0][0] != 0 or pos[1][0] != 0:
                raise RuntimeError(
                    "Inserting in an empty array at a non (0,0) position")
            self.domain_ = np.array([[xyInt]])
            return
        # pos argument has the format
        # (row, moveRowsAtInsert: bool), (column, moveColumnsAtInsert:bool)
        if pos[0][1] == True or pos[0][0] >= self.domain_.shape[0]:
            self.domain_ = np.insert(
                self.domain_, pos[0][0], np.full(
                    (self.domain_.shape[1]), None), 0)
        if pos[1][1] == True or pos[1][0] >= self.domain_.shape[1]:
            self.domain_ = np.insert(
                self.domain_, pos[1][0], np.full(
                    (self.domain_.shape[0]), None), 1)

        self.domain_[pos[0][0], pos[1][0]] = xyInt

    def getInsertionIndex(self, xyInt: KInterval):
        if self.domain_.size == 0:
            return ((0, False), (0, False))

        iidx = None
        closestXIndex = None

        for index, kint in np.ndenumerate(self.domain_):
            if kint is None:
                continue
            if xyInt.x_.overlaps(kint.x_):
                if xyInt.x_ == kint.x_:
                    iidx = (index[1], False)
                    break
                else:
                    raise RuntimeError(
                        "intervals overlap but are not the same")

            if not closestXIndex:
                closestXIndex = index
            else:
                if intervalSize((kint.x_ | xyInt.x_).enclosure) < intervalSize((self.domain_[closestXIndex].x_ | xyInt.x_).enclosure):
                    closestXIndex = index

        jidx = None
        closestYIndex = None
        for index, kint in np.ndenumerate(self.domain_):
            if kint is None:
                continue

            if xyInt.y_.overlaps(kint.y_):
                if xyInt.y_ == kint.y_:
                    jidx = (index[0], False)
                    break
                else:
                    raise RuntimeError(
                        "intervals overlap but are not the same")

            if not closestYIndex:
                closestYIndex = index
            else:
                if intervalSize((kint.y_ | xyInt.y_).enclosure) < intervalSize((self.domain_[closestYIndex].y_ | xyInt.y_).enclosure):
                    closestYIndex = index

        # we check that we are not inserting in the position with an element with the same intervals
        if iidx is not None and jidx is not None and self.domain_[iidx[0]][jidx[0]] is not None:
            if self.domain_[iidx[0]][jidx[0]] == xyInt:
                raise RuntimeError(
                    "Inserting interval in a position that contains element with the same interval")
        # No element in matrix is found with the same interval, we find position based on closed distance to interval element
        if iidx is None:
            # if the closest element was to the left, we place the index in the element next to it
            if self.domain_[closestXIndex].x_ < xyInt.x_:
                # we will only move the column if there is another element to the right
                if self.domain_.shape[1] > closestXIndex[1]+1:
                    iidx = (closestXIndex[1] + 1, True)
                # otherwise is the last column with non null elements and there is not need to move
                else:
                    iidx = (closestXIndex[1] + 1, False)
            else:
                iidx = (closestXIndex[1], True)

        if jidx is None:
            # if the closest element was to the left, we place the index in the element next to it
            if self.domain_[closestYIndex].y_ < xyInt.y_:
                # we will only move the column if there is another element to the right
                if self.domain_.shape[0] > closestYIndex[0]+1:
                    jidx = (closestYIndex[0] + 1, True)
                # otherwise is the last column with non null elements and there is not need to move
                else:
                    jidx = (closestYIndex[0] + 1, False)
            else:
                jidx = (closestYIndex[0], True)

        return (jidx, iidx)
