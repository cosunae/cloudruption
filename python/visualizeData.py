import time
import struct
import numpy as np
import string
import matplotlib.pyplot as plt
import argparse
import time
import dataregistry as dreg
from numba import jit
from confluent_kafka import Consumer, KafkaError
from typing import List
import math
import fieldop
from kafka import KafkaConsumer
# from singleton import sss
import data
import grid_operator as go
import plotly.express as px
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output
import json
import uuid
import plotly.graph_objects as go
import numpy as np
from flask_caching import Cache
import os

processed = {}

reg = dreg.DataRegistryStreaming("group1"+str(uuid.uuid1()))
reg.loadData("visualizeData.yaml")

print("****************************************************")
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='toNetCDF')
    parser.add_argument('--file', help='grib/netcdf filename')

    args = parser.parse_args()

    # if args.file:
    #     reg = dreg.DataRegistryFile(args.file)
    # else:
    #     reg = dreg.DataRegistryStreaming()

    # reg.loadData(__file__.replace(".py", ".yaml"))

    # datapool = data.DataPool()

    # outreg = dreg.OutputDataRegistryFile("ou_ncfile", datapool)

    # structure of type
    # [ {"timestamp": 1583230879, "fields": ["U","V"]}]
    listCompletedFields = []
    datapool = data.DataPool()

#    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

#    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    app = dash.Dash(__name__,  meta_tags=[
        {"name": "viewport", "content": "width=device-width"}])

    CACHE_CONFIG = {
        # try 'filesystem' if you don't want to setup redis
        # 'CACHE_TYPE': 'redis',
        # 'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')
        'CACHE_TYPE': 'filesystem',
        'CACHE_DIR': '/tmp/dash'
        # 'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')
    }
    cache = Cache()
    cache.init_app(app.server, config=CACHE_CONFIG)

    app.layout = html.Div([
        html.Div([
            html.Label('timestamp'),
            dcc.Slider(
                id='timestamp-slider',
                min=0,
                max=0,
                marks={-1: "null"},
                value=0
            ),
            html.Div([
                html.Div(id='plot-container', className="topmargin_box"),
                html.Label('level'),
                dcc.Slider(
                    id='level-slider',
                    min=0,
                    max=0,
                    marks={0: "0"},
                    value=0,
                ), ],
            )
        ], className="pretty_container eight columns"
        ),
        html.Div([
            dash_table.DataTable(
                id='mytable',
                columns=[{"name": "fields", "id": "field"}],
                data=[],
                page_action='native',
                page_current=0,
                page_size=20,
            ),
            # intermediate variable, will have style={'display': 'none'}
            html.Div(id='selected-letter'),
            dcc.Interval(
                id='interval-component',
                interval=1*1000,  # in milliseconds
                n_intervals=0
            ), ],
            className="pretty_container eight columns",
        )
    ], className="row flex-display",)

    def computeOutput(timestampfields):
        mint = 0
        maxt = len(listCompletedFields)-1

        return [[{"field": x} for x in timestampfields], mint, maxt, {i: str(i) for i in range(0, len(listCompletedFields)-1)}]

    @cache.memoize()
    def processCompletedFields(n, timestamp_index):
        global listCompletedFields

        if not listCompletedFields:
            tCompletedFields = []
        else:
            tCompletedFields = listCompletedFields[timestamp_index]["fields"]

        # the callback is called two times per trigger because of this
        # https://github.com/plotly/dash-renderer/pull/54
        if n in processed:
            return computeOutput(tCompletedFields)
        processed[n] = 1

        global reg

        for i in range(30):
            reg.poll(3)
            reqHandle = reg.complete()
            if reqHandle:
                reg.gatherField(reqHandle, datapool)

                allTimestamps = [x["timestamp"] for x in listCompletedFields]
                if reqHandle.timestamp_ not in allTimestamps:
                    listCompletedFields.append(
                        {"timestamp": reqHandle.timestamp_})
                    tCompletedFields = listCompletedFields[-1].setdefault(
                        "fields", [])
                else:
                    tCompletedFields = next(
                        x["fields"] for x in listCompletedFields if x["timestamp"] == reqHandle.timestamp_)

                fields = [x.name for x in reg.groupRequests_[
                    reqHandle.groupId_].reqFields_]
                print('Completed ', fields)
                for x in fields:
                    if x not in tCompletedFields:
                        tCompletedFields.append(x)

        if not listCompletedFields:
            tCompletedFields = []
        else:
            tCompletedFields = listCompletedFields[timestamp_index]["fields"]

        return computeOutput(tCompletedFields)

    @app.callback([Output('mytable', 'data'), Output('timestamp-slider', "min"),
                   Output('timestamp-slider', "max"), Output('timestamp-slider', "marks")],
                  [Input('interval-component', 'n_intervals'), Input('timestamp-slider', "value")])
    def receive_data(n, timestamp_index):
        return processCompletedFields(n, timestamp_index)

    @app.callback(
        [Output('selected-letter', 'children'),
         Output('plot-container', 'children'),
         Output('level-slider', 'max'),
         Output('level-slider', 'marks')
         ],
        [Input('mytable', 'active_cell'), Input('timestamp-slider', 'value'),
         Input('mytable', 'page_current'), Input('mytable', 'page_size'), Input('level-slider', 'value')])
    def update_graphs(active_cell, timestamp_index, page_current, page_size, level):
        global listCompletedFields

        if active_cell:
            print("TIIIIIIIIIIIIIIIIIIIIIIIIIII", timestamp_index)
            timestamp = listCompletedFields[timestamp_index]["timestamp"]
            listFields = listCompletedFields[timestamp_index]["fields"]
            print("ooooooooooooooo", listFields)
            idx = active_cell["row"] + page_current*page_size
            # we are on a page beyond the number of fields
            if idx >= len(listFields):
                return "", "", 0, {0: "0"}

            fieldname = listFields[(
                active_cell["row"] + page_current*page_size)]
            field = datapool[timestamp][fieldname].data_
            fieldarr = np.array(field, copy=False)

            figure = {
                'data': [
                    go.Heatmap(z=fieldarr.transpose()[level, :, :])],
                'layout': dict(
                    margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
                    legend={'x': 0, 'y': 1},
                    hovermode='closest',
                    title=fieldname
                )}

            # , {i: str(i) for i in range(fieldarr.shape[2]-1)}]
            return [fieldname, dcc.Graph(id='plot', figure=figure), (fieldarr.shape[2]-1), {i: str(i) for i in range(fieldarr.shape[2])}]

        return "", "", 0, {0: "0"}

    app.run_server(debug=True)
