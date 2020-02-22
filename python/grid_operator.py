import dataregistry as dreg
import data

class identity:
    def __call__(self, datapool: data.DataPool, timestamp, gbc ):
        pass


class grid_operator:
    def __call__(self, operator, reg: dreg.DataRegistry, datapool: data.DataPool, *, outreg: dreg.OutputDataRegistryFile=None, service=None):
        gbc = {}
        while True:
            reg.poll(1.0)
            reqHandle = reg.complete()
            if reqHandle:
                reg.gatherField(reqHandle, datapool)
                operator(datapool, reqHandle.timestamp_, gbc)
                if outreg:
                    outreg.sendData()
                if not service:
                    break

