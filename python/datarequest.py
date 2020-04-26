from dataclasses import dataclass
import data
import fieldop
import domain_intervals as di
import portion as P


@dataclass
class DataRequest:

    def __init__(self, user_data_req: data.UserDataReq):
        self.user_data_req_: data.UserDataReq = user_data_req
        self.patches_ = []
        self.npatches_ = None
        self.completedPatches_ = []
        self.completedDomainInterval = di.domain_intervals()
        self.datadesc_ = None

    def insert(self, patch: fieldop.SinglePatch, msgKey: data.MsgKey):
        self.patches_.append(patch)

        if not self.datadesc_:
            # in case there is a user request frame, the received data
            # is framed within the user request frame
            if self.user_data_req_.data_desc:
                data_desc = self.user_data_req_.data_desc

                dx = (msgKey.longitudeOfLastGridPoint -
                      msgKey.longitudeOfFirstGridPoint) / msgKey.lonlen
                ifirst = int((data_desc.longitudeOfFirstGridPoint -
                              msgKey.longitudeOfFirstGridPoint) / dx)
                ilast = msgKey.lonlen - 1 - int((msgKey.longitudeOfLastGridPoint -
                                                 data_desc.longitudeOfLastGridPoint) / dx)
                dy = (msgKey.longitudeOfLastGridPoint -
                      msgKey.longitudeOfFirstGridPoint) / msgKey.lonlen
                jfirst = int((data_desc.latitudeOfFirstGridPoint -
                              msgKey.latitudeOfFirstGridPoint) / dy)
                jlast = msgKey.latlen - 1 - int((msgKey.latitudeOfLastGridPoint -
                                                 data_desc.latitudeOfLastGridPoint) / dy)
                userReqIndexFrame = [ifirst, ilast, jfirst, jlast]
                userReqCoordFrame = [data_desc.longitudeOfFirstGridPoint, data_desc.longitudeOfLastGridPoint,
                                     data_desc.latitudeOfFirstGridPoint, data_desc.latitudeOfLastGridPoint]
            else:
                userReqIndexFrame = [0, msgKey.lonlen-1, 0, msgKey.latlen-1]
                userReqCoordFrame = [msgKey.longitudeOfFirstGridPoint, msgKey.longitudeOfLastGridPoint,
                                     msgKey.latitudeOfFirstGridPoint, msgKey.latitudeOfLastGridPoint]

            self.datadesc_ = fieldop.DataDesc(*userReqCoordFrame,
                                              *userReqIndexFrame,
                                              msgKey.datetime, msgKey.ilonstart, msgKey.jlatstart, msgKey.level,
                                              msgKey.totlonlen, msgKey.totlatlen, msgKey.levlen)
        else:
            assert self.datadesc_.longitudeOfFirstGridPoint == msgKey.longitudeOfFirstGridPoint
            assert self.datadesc_.longitudeOfLastGridPoint == msgKey.longitudeOfLastGridPoint
            assert self.datadesc_.latitudeOfFirstGridPoint == msgKey.latitudeOfFirstGridPoint
            assert self.datadesc_.latitudeOfLastGridPoint == msgKey.latitudeOfLastGridPoint
            assert self.datadesc_.datetime == msgKey.datetime
#            assert self.datadesc_.ilonstart == msgKey.ilonstart
#            assert self.datadesc_.jlatstart == msgKey.jlatstart
            assert self.datadesc_.totlonlen == msgKey.totlonlen
            assert self.datadesc_.totlatlen == msgKey.totlatlen
            self.datadesc_.levelstart = min(
                self.datadesc_.levelstart, msgKey.level)
            # TODO recover
            assert self.datadesc_.levlen == msgKey.levlen

        if not self.npatches_:
            self.npatches_ = msgKey.npatches
        else:
            assert self.npatches_ == msgKey.npatches

        # TODO check in the else the keymsg is compatible with others msgs

    def computePatchInterval(self, patch):
        return di.KInterval(P.closedopen(patch.ilonstart(), patch.ilonstart() + patch.lonlen()),
                            P.closedopen(patch.jlatstart(),
                                         patch.jlatstart() + patch.latlen()))

    def transferCompletedPatches(self, xyInt):
        # TODO we need to do this cause the value is None, even if it is init as []
        if not self.completedPatches_:
            self.completedPatches_ = [
                x for x in self.patches_ if self.computePatchInterval(x) == xyInt]
        else:
            self.completedPatches_.extend(
                [x for x in self.patches_ if self.computePatchInterval(x) == xyInt])

        self.patches_[:] = [
            x for x in self.patches_ if self.computePatchInterval(x) != xyInt]

    def complete(self) -> bool:
        # Not a single patch was inserted
        if not self.datadesc_:
            return False

        levels = {}
        for patch in self.patches_:
            kint = self.computePatchInterval(patch)
            levels.setdefault(kint, 0)
            levels[kint] += 1

        for xyInt, nlev in levels.items():
            if self.completedDomainInterval.findInterval(xyInt) is not None:
                raise RuntimeError(
                    "Found a patch on an interval that was already inserted")
            if self.completedDomainInterval.overlaps(xyInt):
                raise RuntimeError("Interval of patch ", xyInt,
                                   " overlaps with other patches collected")
            if nlev == self.datadesc_.levlen:
                self.completedDomainInterval.insertInterval(xyInt)
                self.transferCompletedPatches(xyInt)

        if self.completedDomainInterval.complete(self.datadesc_):
            return True
        return False
