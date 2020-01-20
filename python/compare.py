import time
from confluent_kafka import Consumer, KafkaError
import struct
from dataclasses import dataclass
import numpy as np
import string
import matplotlib.pyplot as plt
from enum import IntEnum

class ActionType(IntEnum):
    InitFile = 0
    Data = 1
    CloseFile = 2

@dataclass
class MsgKey:
    action_type: int
    key: str
    npatches: int
    mpirank: int
    ilonstart: int
    jlatstart: int
    level: int
    dlon: float
    dlat: float
    lonlen: int
    latlen: int
    levlen: int
    totlonlen: int
    totlatlen: int

@dataclass
class DataRequest:
    fieldname_: str
    patches_: []
    npatches_: -1
    nlevels_: -1

    def __init__(self, fieldname):
        self.fieldname_=fieldname
        self.patches_=[]
        self.npatches_=-1
        self.nlevels_=-1
    def insert(self, patch, msgKey: MsgKey):
        self.patches_.append(patch)
        if self.npatches_ == -1:
            print("KK " , msgKey.npatches)
            self.npatches_ = msgKey.npatches
            self.nlevels_ = msgKey.levlen

    def complete(self) -> bool:
        print("TEST " , len(self.patches_), self.npatches_)
        return (len(self.patches_) == self.npatches_*self.nlevels_) and len(self.patches_) != 0
@dataclass
class DataRegistry:
    dataRequests_: {}
    c_ = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id' : 'group1',
        'auto.offset.reset': 'earliest'
    })

    def __init__(self):
        self.dataRequests_ = {}
        self.c_ = Consumer({
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'group1',
            'auto.offset.reset': 'earliest'
        })

    def __del__(self):
        self.c_.close()

    def subscribe(self, topics):
        for fieldname in topics:
            self.dataRequests_[fieldname] = DataRequest(fieldname)
        print("subscribing to ", topics)
        self.c_.subscribe(topics)

    def poll(self,seconds):
        msg = self.c_.poll(seconds)

        if msg is None:
            print("cont")
            return -1
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            return -1

        print("NNN")
        dt = np.dtype('<f4')
        al = np.frombuffer(msg.value(), dtype=dt)
        msgkey = get_key(msg.key())

        if msgkey.action_type != int(ActionType.Data):
            return

        if msgkey.key[0] in self.dataRequests_.keys():
            field = msgkey.key[0]
            print("ADD", field)

            reg.dataRequests_[field].insert(np.reshape(al, (msgkey.lonlen, msgkey.latlen)), msgkey)

    def complete(self) -> bool:
        for req in self.dataRequests_.values():
            if not req.complete():
                return False
        return True

def get_key(msg):
    c1 = struct.unpack('i8c2i3Q2f5Q', msg)
    stringlist=''.join([x.decode('utf-8') for x in c1[1:9]])
    allargs = list(c1[0:1])+[stringlist] + list(c1[9:])
    return MsgKey(*allargs)

if __name__ == '__main__':
    reg = DataRegistry()
    reg.subscribe(["u", "v"])

    vert_prof = None

    while True:
        reg.poll(1.0)
        if reg.complete():
            print("COMPLETE")
            break




