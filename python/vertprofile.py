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

def get_key(msg):
    c1 = struct.unpack('i8c2i3Q2f5Q', msg)
    stringlist=''.join([x.decode('utf-8') for x in c1[1:9]])
    allargs = list(c1[0:1])+[stringlist] + list(c1[9:])
    return MsgKey(*allargs)

if __name__ == '__main__':
    c = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id' : 'group1',
        'auto.offset.reset': 'earliest'
    })

    c.subscribe(['v'])

    vert_prof = None

    lvlcnt={}
    while True:
        msg = c.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            print("Consumer error: {}".format(msg.error()))
            continue

        dt = np.dtype('<f4')
        al = np.frombuffer(msg.value(), dtype=dt)
        msgkey = get_key(msg.key())
        if msgkey.action_type != int(ActionType.Data):
            continue

        if msgkey.key[0] == str('v'):

            ipos=30
            jpos=30

            if ((msgkey.ilonstart <= ipos <= msgkey.ilonstart + msgkey.lonlen) and
                (msgkey.jlatstart <= jpos <= msgkey.jlatstart + msgkey.latlen)):

                if vert_prof is None:
                    vert_prof = np.empty([msgkey.levlen])
                    lvlcnt[msgkey.key] = 0

                vert_prof[msgkey.level] = al[0]

                lvlcnt[msgkey.key] = lvlcnt[msgkey.key]+1
                if lvlcnt[msgkey.key] == msgkey.levlen:
                    plt.plot(vert_prof)
                    plt.show()
    c.close()


