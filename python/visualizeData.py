#!/usr/bin/python3.7
import time
import re
import struct
import numpy as np
import string
import argparse
import time
import dataregistry as dreg
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
from confluent_kafka import Consumer
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
import sd_material_ui


@dataclass
class fieldwrap:
    name: str
    is2d: bool


class NoValidKafkaBroker(Exception):
    pass


print("****************************************************")
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='toNetCDF')
    parser.add_argument('-v', default=False, action='store_true')

    args = parser.parse_args()

    verboseprint = print if args.v else lambda *a, **k: None

    app = dash.Dash()

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

    datapool = data.DataPool()
    reg = None

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
                sd_material_ui.Snackbar(
                    id='snackbar-kafka', open=False, message='')
            ]),
            html.Label('timestamp'),
            dcc.Slider(
                id='timestamp-slider',
                min=0,
                max=0,
                marks={-1: "null"},
                value=-1
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
                id='topics-table',
                columns=[{"name": "kafka topics", "id": "topics"}],
                data=[],
                page_action='native',
                page_current=0,
                page_size=10,
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
            sd_material_ui.Snackbar(
                id='snackbar-selecttopic', open=False, message=''),
            html.Div([dash_table.DataTable(
                id='received-data',
                columns=[{"name": "2d fields", "id": "2d_field"},
                         {"name": "3d fields", "id": "3d_field"}],
                data=[],
                page_action='native',
                page_current=0,
                page_size=10,
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
            ), ], className="pretty_container six columns",),
            dcc.Interval(
                id='interval-component',
                interval=1*1000,  # in milliseconds
                n_intervals=0
            ),
            dcc.Interval(
                id='interval-component-collect',
                interval=4*1000,  # in milliseconds
                n_intervals=0
            ),
            html.Div(id='dummy'),
        ],
            className="pretty_container four columns",
        )
    ], className="row flex-display",)

    def computeOutput(datapool):

        list2dFields = []
        list3dFields = []
        for timestamp in datapool.timestamps():
            for fieldname in datapool[timestamp]:
                if datapool[timestamp][fieldname].datadesc_.levlen == 1:
                    list2dFields.append(fieldname)
                else:
                    list3dFields.append(fieldname)

        # remove duplicates
        list2dFields = list(dict.fromkeys(list2dFields))
        list3dFields = list(dict.fromkeys(list3dFields))

        fdict = []

        for f2, f3 in itertools.zip_longest(list2dFields, list3dFields):
            elemdict = {}
            if f2:
                elemdict["2d_field"] = f2
            if f3:
                elemdict["3d_field"] = f3

            fdict.append(elemdict)

        return fdict

    def processCompletedFields():
        global reg

        for i in range(3):
            reg.poll(0.5)

            reqHandle = reg.complete()
            if reqHandle:
                reg.gatherField(reqHandle, datapool)
                fields = [x.name for x in reg.groupRequests_[
                    reqHandle.groupId_].reqFields_]
                verboseprint('list of (complete) collected fields: ', fields)

    @app.callback([dash.dependencies.Output('snackbar-kafka', 'open'),
                   dash.dependencies.Output('snackbar-kafka', 'message'), dash.dependencies.Output('kafka_broker_title', 'children')],
                  [Input('kafka-submit-buttom', 'n_clicks')],
                  [State("input_kafka_broker", "value")])
    def update_kafka_broker(n_clicks, kafka_broker):
        global reg
        if n_clicks == 0:
            raise PreventUpdate
        if not kafka_broker:
            return True, "Error: kafka broker not set", ""

        reg = dreg.DataRegistryStreaming(
            broker=kafka_broker, group="group1" + str(uuid.uuid1()))

        return True, "Setting kafka broker: "+kafka_broker, "kafka broker: "+kafka_broker

    def get_topics(kafka_broker):
        c_ = Consumer({
            'bootstrap.servers': kafka_broker,
            'group.id': "group"+str(uuid.uuid1()),
            'auto.offset.reset': 'earliest'
        })

        try:
            topics = c_.list_topics(timeout=2).topics
        except:
            raise NoValidKafkaBroker("no valid broker: ", kafka_broker)

        return topics

    @app.callback(Output('topics-table', 'data'),
                  [Input('interval-component', 'n_intervals')],
                  [State('input_kafka_broker', 'value'), State(
                      'kafka-submit-buttom', 'n_clicks')]
                  )
    def update_list_topics(n_intervals, kafka_broker, n_clicks):
        # kafka broker not set yet
        if n_clicks == 0:
            raise PreventUpdate
        topics = None
        try:
            topics = get_topics(kafka_broker)
        except Exception as ex:
            print(ex)
            raise PreventUpdate

        return [{"topics": x} for x in topics]

    @app.callback([Output('received-data', 'data')],
                  [Input('interval-component', 'n_intervals')],
                  [State('input_kafka_broker', 'value'), State(
                      'kafka-submit-buttom', 'n_clicks')]
                  )
    def update_data_collected(n, kafka_broker, n_clicks):
        # kafka broker not set yet
        if n_clicks == 0:
            raise PreventUpdate

        data = computeOutput(datapool)

        return [data]

    @app.callback([Output('dummy', 'children')],
                  [Input('interval-component-collect', 'n_intervals')],
                  [State('input_kafka_broker', 'value'), State(
                      'kafka-submit-buttom', 'n_clicks')]
                  )
    def update_received_data(n, kafka_broker, n_clicks):
        # kafka broker not set yet
        if n_clicks == 0:
            raise PreventUpdate

        if not reg:
            raise PreventUpdate

        try:
            filename = "___lockfile." + '.lock'
            with FileLock(filename):
                processCompletedFields()
        except Exception as ex:
            print("Error", ex)
            raise PreventUpdate
        return ['']

    def findTimestampsWithField(datapool, fieldname):
        return [tstamp for tstamp in datapool.timestamps() if fieldname in datapool[tstamp]]

    @app.callback([dash.dependencies.Output('snackbar-selecttopic', 'open'),
                   dash.dependencies.Output('snackbar-selecttopic', 'message')], [Input('topics-table', 'active_cell'),
                                                                                  Input('topics-table', 'page_current'), Input('topics-table', 'page_size')],
                  [State('topics-table', 'data')])
    def select_data(topics_cell, topics_page, topics_psize, topics_data):

        global reg
        # No cell has been selected yet
        if not topics_cell:
            raise PreventUpdate
        cidx = topics_page*topics_psize + topics_cell['row']
        if cidx > len(topics_data):
            print("Error: selected cell does not exists in data table")
            raise PreventUpdate

        topic = topics_data[cidx]['topics']
        topicPrefix = re.findall(r'.*?_', topic)[0]
        field = re.sub(topicPrefix, "", topic)

        reg.subscribe(topicPrefix, [data.UserDataReq(field, None)])

        return True, "subscribed to " + field

    @app.callback(
        [Output('plot-container', 'children'),
         Output('level-slider', 'max'),
         Output('level-slider', 'marks'),
         Output('timestamp-slider', 'min'), Output('timestamp-slider',
                                                   'max'), Output('timestamp-slider', 'marks')
         ],
        [Input('received-data', 'active_cell'), Input('received-data', 'page_current'), Input('received-data', 'page_size'),
         Input('received-data', 'data'),
         Input('timestamp-slider', 'value'), Input('level-slider', 'value')])
    def update_graphs(active_cell, page_current, page_size, fields_table, timestamp_index,  level):
        if not active_cell:
            raise PreventUpdate

        dimkey = "2d_field" if (active_cell["column"] == 0) else "3d_field"
        idx = active_cell["row"] + page_current*page_size
        # row pointing to non existing row in this page (happens when moving page)
        if len(fields_table) <= idx:
            raise PreventUpdate

        fieldname = fields_table[idx][dimkey]

        timestamps = sorted(findTimestampsWithField(datapool, fieldname))

        if not timestamps:
            raise Exception("no single timestamp found for field ", fieldname)

        timestamp = timestamps[0] if timestamp_index == -1 else timestamp_index

        # In case the input that trigger the callback is not the table selection, but the timestamp-slider
        # it can happen that the cell selected is pointing to an out of range in the new timestamp-slider
        # In that case the fieldname returned by getFieldnameFromList is None
        if fieldname is None:
            raise PreventUpdate

        field = datapool[timestamp][fieldname].data_
        fieldarr = np.array(field, copy=False)

        # Level slides is pointing to a previous value from a field that had more levels than the current field
        if level >= fieldarr.shape[2]:
            raise PreventUpdate

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
        return [dcc.Graph(id='plot', figure=figure), (fieldarr.shape[2]-1), {i: str(i) for i in range(fieldarr.shape[2])}, timestamps[0], timestamps[-1], {i: str(i) for i in timestamps}]

    app.run_server(debug=True, host='0.0.0.0', port=3001)
