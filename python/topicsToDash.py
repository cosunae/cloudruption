import time
import struct
import numpy as np
import string
import matplotlib.pyplot as plt
import argparse
import time
import dataregistry as dreg
from numba import jit
from typing import List
import math
import fieldop
import data
import grid_operator as go
import plotly.express as px
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='toNetCDF')
    parser.add_argument('--file', help='grib/netcdf filename')

    args = parser.parse_args()
    if args.file:
        reg = dreg.DataRegistryFile(args.file)
    else:
        reg = dreg.DataRegistryStreaming()

    reg.loadData(__file__.replace(".py", ".yaml"))

    datapool = data.DataPool()

    outreg = dreg.OutputDataRegistryFile("ou_ncfile", datapool)

    listCompletedFields = ["None"]

    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

    app.layout = html.Div([
        dash_table.DataTable(
            id='table',
            columns=[{"name": "fields", "id": "field"}],
            data=[{"field": "U"}],
            editable=True,
        ),
        html.H3(
            id='text-output',
            children='',
            style={'textAlign': 'left'}
        ),
        dcc.Interval(
            id='interval-component',
            interval=1*1000,  # in milliseconds
            n_intervals=0
        )
        #        dcc.Graph(
        #            id='life-exp-vs-gdp',
        #        ),
        #        html.Label('level'),
        #        dcc.Slider(
        #            id='level-slider',
        #            min=0,
        #            max=u.shape[1],
        #            marks={i: str(i) for i in range(1, u.shape[1])},
        #            value=5,
        #        ),
    ])

    @app.callback(Output('table', 'data'),
                  [Input('interval-component', 'n_intervals')])
    def update_metrics(n):
        while True:
            reg.poll(1.0)
            reqHandle = reg.complete()
            print("Primo ", reqHandle)
            if reqHandle:
                print("AAAAAA", listCompletedFields)
                print("REQ*************************", reqHandle.groupId_, reqHandle.timestamp_, [
                    x.name for x in reg.groupRequests_[reqHandle.groupId_].reqFields_])

                if listCompletedFields == ["None"]:
                    listCompletedFields = []

                listCompletedFields.extend([x.name for x in reg.groupRequests_[
                    reqHandle.groupId_].reqFields_])
        #    listCompletedFields = listCompletedFields + \
        #        [x.name for x in reg.groupRequests_[reqHandle.groupId_].reqFields_]

                reg.gatherField(reqHandle, datapool)

            print("ll-------------------------------------------",
                  [{"field": x} for x in listCompletedFields])
            return [{"field": x} for x in listCompletedFields]

    app.run_server(debug=True)

#    while True:
#        reg.poll(1.0)
#        reqHandle = reg.complete()
#        if reqHandle:
#            print("AAAAAA", listCompletedFields)
#            print("REQ*************************", reqHandle.groupId_, reqHandle.timestamp_, [
#                  x.name for x in reg.groupRequests_[reqHandle.groupId_].reqFields_])

#            listCompletedFields = listCompletedFields + \
#                [x.name for x in reg.groupRequests_[reqHandle.groupId_].reqFields_]

#            reg.gatherField(reqHandle, datapool)
#            outreg.sendData()
#        print("test")
