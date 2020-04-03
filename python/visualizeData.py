#!/usr/bin/python3
import time
import struct
import numpy as np
import string
import argparse
import time
import dataregistry as dreg
from numba import jit
from confluent_kafka import Consumer, KafkaError
from typing import List
import math
import fieldop
# from singleton import sss
import data
import grid_operator as go
import plotly.express as px
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
import json
import uuid
import plotly.graph_objects as go
import numpy as np
from flask_caching import Cache
import os
from dataclasses import dataclass
import itertools
import sd_material_ui
from dash.exceptions import PreventUpdate
from filelock import FileLock

processed = {}

reg = None

@dataclass
class fieldwrap:
    name: str
    is2d: bool


print("****************************************************")
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='toNetCDF')
    parser.add_argument('--file', help='grib/netcdf filename')

    args = parser.parse_args()

    app = dash.Dash(__name__,  meta_tags=[
        {"name": "viewport", "content": "width=device-width"}])

    # structure of type
    # [ {"timestamp": 1583230879, "fields": [fieldwrap("U",False),fieldwrap("V",False), fieldwrap("TMIN_2M", True)]}]
    listCompletedFields = []
    datapool = data.DataPool()

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
            html.Div(id="kafka_title", children="kafka broker"),
            html.Div([
                html.Div([
                    dcc.Input(
                        id="input_kafka_broker".format("text"),
                        type="text",
                        placeholder="kafka broker".format("text"),
                    ),
                    html.Button(id='kafka-submit-buttom',
                                n_clicks=0, children='Submit'),
                    html.Div(id="kafka_broker_title"),
                ], className="bare_container"),
                sd_material_ui.Snackbar(id='snackbar-kafka', open=False, message='')
            ]),
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
                html.Div([
                    dcc.Slider(
                        id='level-slider',
                        min=0,
                        max=0,
                        marks={0: "0"},
                        value=0,
                    )],
                )
            ],
            )
        ], className="pretty_container ten columns"
        ),
        html.Div([
            dash_table.DataTable(
                id='mytable',
                columns=[{"name": "2d fields", "id": "2d_field"},
                         {"name": "3d fields", "id": "3d_field"}],
                data=[],
                page_action='native',
                page_current=0,
                page_size=20,
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                style_cell_conditional=[
                    {
                        'if': {'column_id': c},
                        'textAlign': 'left',
                        'else': 'right'
                    } for c in ['2d_field']
                ]
            ),
            # intermediate variable, will have style={'display': 'none'}
            html.Div(id='selected-letter'),
            dcc.Interval(
                id='interval-component',
                interval=1*1000,  # in milliseconds
                n_intervals=0
            ), ],
            className="pretty_container four columns",
        )
    ], className="row flex-display",)

    def computeOutput(timestampfields):
        # timestampfields
        # [fieldwrap("name", is2d=True)]
        mint = 0
        maxt = len(listCompletedFields)-1

        list2dFields = [x.name for x in timestampfields if x.is2d]
        list3dFields = [x.name for x in timestampfields if not x.is2d]

        fdict = []
        for f2, f3 in itertools.zip_longest(list2dFields, list3dFields):
            elemdict = {}
            if f2:
                elemdict["2d_field"] = f2
            if f3:
                elemdict["3d_field"] = f3

            fdict.append(elemdict)

        print('GGGG', fdict)
        return [fdict, mint, maxt, {i: str(i) for i in range(0, len(listCompletedFields)-1)}]

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
            reg.poll(0.1)
            reqHandle = reg.complete()
            if reqHandle:
                timestamp = reqHandle.timestamp_

                reg.gatherField(reqHandle, datapool)

                allTimestamps = [x["timestamp"] for x in listCompletedFields]
                if reqHandle.timestamp_ not in allTimestamps:
                    listCompletedFields.append(
                        {"timestamp": reqHandle.timestamp_})
                    tCompletedFields = listCompletedFields[-1].setdefault(
                        "fields", [])
                else:
                    # find the timestamp element
                    tCompletedFields = next(
                        x["fields"] for x in listCompletedFields if x["timestamp"] == reqHandle.timestamp_)

                fields = [x.name for x in reg.groupRequests_[
                    reqHandle.groupId_].reqFields_]
                print('Completed ', fields)
                for field in fields:
                    datadesc = datapool[timestamp][field].datadesc_

                    is2d = True if datadesc.levlen == 1 else False
                    if field not in [p.name for p in tCompletedFields]:
                        tCompletedFields.append(fieldwrap(field, is2d))

        if not listCompletedFields:
            tCompletedFields = []
        else:
            tCompletedFields = listCompletedFields[timestamp_index]["fields"]

        return computeOutput(tCompletedFields)

    @app.callback([dash.dependencies.Output('snackbar-kafka', 'open'),
                   dash.dependencies.Output('snackbar-kafka', 'message'), dash.dependencies.Output('kafka_broker_title','children')],
                  [Input('kafka-submit-buttom', 'n_clicks')],
                  [State("input_kafka_broker", "value")])
    def update_kafka_broker(n_clicks, kafka_broker):
        global reg
        if n_clicks == 0:
            raise PreventUpdate
        if not kafka_broker:
            return True, "Error: kafka broker not set",""

        reg = dreg.DataRegistryStreaming(broker=kafka_broker, group="group1" + str(uuid.uuid1()))
        reg.loadData("visualizeData.yaml")

        return True,"Setting kafka broker: "+kafka_broker,"kafka broker: "+kafka_broker

    @app.callback([Output('mytable', 'data'), Output('timestamp-slider', "min"),
                   Output('timestamp-slider', "max"), Output('timestamp-slider', "marks")],
                  [Input('interval-component', 'n_intervals'), Input('timestamp-slider', "value")])
    def receive_data(n, timestamp_index):
        if not reg:
            raise PreventUpdate

        filename = "___lockfile." + str(timestamp_index) + '.lock'
        with FileLock(filename):
            data,min,max,slmarks = processCompletedFields(n, timestamp_index)
        return data,min,max,slmarks

    def getFieldnameFromList(fieldIs2d, listFields, elementid):
        # listFields in format [fieldwrap("U",False),fieldwrap("V",False), fieldwrap("TMIN_2M", True)]
        cnt = 0
        for f in listFields:
            if f.is2d != fieldIs2d:
                continue
            if cnt == elementid:
                return f.name
            cnt += 1

        return None

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
            timestamp = listCompletedFields[timestamp_index]["timestamp"]
            listFields = listCompletedFields[timestamp_index]["fields"]
            idx = active_cell["row"] + page_current*page_size
            # we are on a page beyond the number of fields
            if idx >= len(listFields):
                return "", "", 0, {0: "0"}

            fieldIs2d = False
            if active_cell["column"] == 0:
                fieldIs2d = True

            fieldname = getFieldnameFromList(
                fieldIs2d, listFields, active_cell["row"] + page_current*page_size)

            #In case the input that trigger the callback is not the table selection, but the timestamp-slider
            #it can happen that the cell selected is pointing to an out of range in the new timestamp-slider
            #In that case the fieldname returned by getFieldnameFromList is None
            if fieldname is None:
                raise PreventUpdate

            field = datapool[timestamp][fieldname].data_
            fieldarr = np.array(field, copy=False)

            figure = {
                'data': [
                    go.Heatmap(z=fieldarr.transpose()[level, :, :])],
                'layout': dict(
                    margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
                    width=1000,
                    height=600,
                    legend={'x': 0, 'y': 1},
                    hovermode='closest',
                    title=fieldname
                )}

            # , {i: str(i) for i in range(fieldarr.shape[2]-1)}]
            return [fieldname, dcc.Graph(id='plot', figure=figure), (fieldarr.shape[2]-1), {i: str(i) for i in range(fieldarr.shape[2])}]

        return "", "", 0, {0: "0"}

    app.run_server(debug=True)
