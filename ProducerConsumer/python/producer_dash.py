import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import plotly.express as px
import plotly.graph_objs as go
import squarify
import boto3
from anytree import Node, RenderTree, AsciiStyle, PreOrderIter
import argparse
import subprocess
import json
import pathlib
import os
from confluent_kafka import Consumer, admin, KafkaError
import time
import uuid
import re
from dash.exceptions import PreventUpdate
from enum import Enum

app = dash.Dash()
producer = None
producerConfig = None
pgrib = None


class Error(Enum):
    NO_ERROR = 1
    NO_VALID_BROKER = 2
    CAN_NOT_GET_LOCK = 3


ErrorToString = {
    Error.NO_ERROR: "Success",
    Error.NO_VALID_BROKER: "url is not a valid kafka broker",
    Error.CAN_NOT_GET_LOCK: "could not acquire a lock for the producer"
}


def insertTree(rootNode, path):
    if not path:
        return
    child = path[0]
    matches = [x for x in rootNode.children if x.name == child]
    if not matches:
        cNode = Node(child, rootNode)
        nextNode = cNode
    else:
        assert len(matches) == 1
        nextNode = matches[0]
    if len(path) > 1:
        insertTree(nextNode, path[1:])


def create_treemap():

    # plotly colorscales
    # One of the following named colorscales:
    #         ['aggrnyl', 'agsunset', 'algae', 'amp', 'armyrose', 'balance',
    #          'blackbody', 'bluered', 'blues', 'blugrn', 'bluyl', 'brbg',
    #          'brwnyl', 'bugn', 'bupu', 'burg', 'burgyl', 'cividis', 'curl',
    #          'darkmint', 'deep', 'delta', 'dense', 'earth', 'edge', 'electric',
    #          'emrld', 'fall', 'geyser', 'gnbu', 'gray', 'greens', 'greys',
    #          'haline', 'hot', 'hsv', 'ice', 'icefire', 'inferno', 'jet',
    #          'magenta', 'magma', 'matter', 'mint', 'mrybm', 'mygbm', 'oranges',
    #          'orrd', 'oryel', 'peach', 'phase', 'picnic', 'pinkyl', 'piyg',
    #          'plasma', 'plotly3', 'portland', 'prgn', 'pubu', 'pubugn', 'puor',
    #          'purd', 'purp', 'purples', 'purpor', 'rainbow', 'rdbu', 'rdgy',
    #          'rdpu', 'rdylbu', 'rdylgn', 'redor', 'reds', 'solar', 'spectral',
    #          'speed', 'sunset', 'sunsetdark', 'teal', 'tealgrn', 'tealrose',
    #          'tempo', 'temps', 'thermal', 'tropic', 'turbid', 'twilight',
    #          'viridis', 'ylgn', 'ylgnbu', 'ylorbr', 'ylorrd']
    client = boto3.client('s3')
    buckets = client.list_buckets()['Buckets']
    root = Node("buckets")

    for bucket in [x['Name'] for x in buckets]:
        b = Node(bucket, parent=root)
        for obj in client.list_objects(Bucket=bucket)['Contents']:
            path = obj['Key'].split('/')
            insertTree(b, path)

    names = [node.name for node in PreOrderIter(root)]
    parents = [
        node.parent.name if node.parent else "" for node in PreOrderIter(root)]

    figure = go.Figure(go.Treemap(
        labels=names,
        parents=parents,
        # bupu pubugn
        # https://community.plot.ly/t/what-colorscales-are-available-in-plotly-and-which-are-the-default/2079
        marker=dict(colorscale='tempo'),
        tiling={"squarifyratio": 4})
    )
#    data = dict(character=names, parent=parents)
#    figure = go.Figure()

#    figure.add_trace(go.Sunburst(
#        labels=names,
#        parents=parents,
#        domain=dict(column=1),
#        marker=dict(colorscale='Electric'),
#        insidetextorientation='radial'))

    figure.update_layout(uniformtext=dict(
        minsize=8, mode='show'), margin=dict(t=10, l=0, r=0, b=10))
    return figure


def get_topics(kafka_broker):
    c_ = Consumer({
        'bootstrap.servers': kafka_broker,
        'group.id': "group"+str(uuid.uuid1()),
        'auto.offset.reset': 'earliest',
    })

    try:
        topics = c_.list_topics(timeout=2).topics
    except:
        return [Error.NO_VALID_BROKER, []]

    return [Error.NO_ERROR, topics]


def launchProducer(kafka_broker, filename):

    filename = pathlib.Path(filename)
    filenameflat = pathlib.Path(str(filename).replace('/', "_"))
    if get_topics(kafka_broker)[0] != Error.NO_ERROR:
        return get_topics(kafka_broker)[0]

    cdir = pathlib.Path(__file__).parent.absolute()
    tmpdir = cdir / pathlib.Path('tmpdash___')
    if not pathlib.Path(tmpdir).exists():
        os.mkdir(tmpdir)
    lockf = tmpdir / filenameflat.with_suffix(".rlock")

    # Can not acquire lock
    if pathlib.Path(lockf).exists():
        return Error.CAN_NOT_GET_LOCK

    fparts = str(filename).split('/')
    bucket = fparts[1]
    key = str('/').join(fparts[2:])

    localfile = str(tmpdir / filename).replace('/', '_')
    s3 = boto3.resource('s3')
    s3.Object(bucket, key).download_file(localfile)

    jfile = open(producerConfig, "r")
    jdata = json.load(jfile)
    jfile.close()
    jdata['kafkabroker'] = kafka_broker
    jdata['parsegrib'] = pgrib
    jdata['lockfile'] = str(lockf)
    jdata['files'] = [localfile]

    tconfig = tmpdir / filenameflat.with_suffix(".configtmp.json")
    jfile = open(tconfig, "w")
    json.dump(jdata, jfile)
    jfile.close()

    f = open("out.log", "w")
    subprocess.call([producer, tconfig], stdout=f)

    return Error.NO_ERROR


def delete_kafka_topics(kafka_broker, topic_regex):
    registered_topics = get_topics(kafka_broker)
    if registered_topics[0] != Error.NO_ERROR:
        return registered_topics[0]

    kba = admin.AdminClient({'bootstrap.servers': kafka_broker})

    """ delete topics """

    # Call delete_topics to asynchronously delete topics, a future is returned.
    # By default this operation on the broker returns immediately while
    # topics are deleted in the background. But here we give it some time (30s)
    # to propagate in the cluster before returning.
    #
    # Returns a dict of <topic,future>.
    topics = []
    regtopic = re.compile(topic_regex)
    for artop in registered_topics[1]:
        if regtopic.match(artop):
            topics.append(artop)

    if not topics:
        return []

    fs = kba.delete_topics(topics, operation_timeout=30)

    # Wait for operation to finish.
    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            print("Topic {} deleted".format(topic))
        except Exception as e:
            print("Failed to delete topic {}: {}".format(topic, e))

    return topics


if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='test.py')
    parser.add_argument(
        '--producer', help='path to producer executable', required=True)
    parser.add_argument(
        '--config', help='path to producer config file template', required=True)
    parser.add_argument(
        '--pgrib', help='path to parseGrib executable', required=True)

    args = parser.parse_args()

    producer = args.producer
    producerConfig = args.config
    pgrib = args.pgrib

    app.layout = html.Div([
        html.Div([
            html.Div([
                html.Div(id="kafka_title", children="kafka broker"),
                html.Div([
                    dcc.Input(
                        id="input_kafka_broker".format("text"),
                        type="text",
                        placeholder="kafka broker".format("text"),
                    ),
                    html.Div(id="kafka_broker_title"),
                ]),
                html.Div([
                    dcc.Input(
                        id="delete_topics".format("text"),
                        type="text",
                        placeholder="delete topics regex".format("text"),
                    ),
                    html.Button(id='submit-buttom',
                                n_clicks=0, children='Submit'),
                    html.Div(id='deleting-text')
                ]),
            ]),
            html.Div([
                dcc.Graph(id='treemap', figure=create_treemap()),
                html.Div(id='launching-producer-text-display')
            ])
        ], className="pretty_container eight columns"),
        html.Div([
            dash_table.DataTable(
                id='topics-table',
                columns=[{"name": "kafka topics", "id": "topics"}],
                data=[],
                page_action='native',
                page_current=0,
                page_size=20,
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                }
            ),
            dcc.Interval(
                id='interval-component',
                interval=1*1000,  # in milliseconds
                n_intervals=0
            )
        ], className="pretty_container two columns")
    ])

    @app.callback(Output('deleting-text', 'children'), [Input('submit-buttom', 'n_clicks')], [State('delete_topics', 'value'), State("input_kafka_broker", "value")])
    def delete_topics_cb(n_clicks, regex, kafka_broker):
        if regex is None:
            raise PreventUpdate

        topics_to_be_deleted = delete_kafka_topics(kafka_broker, regex)
        return "deleting topics: "+",".join(topics_to_be_deleted)

    @app.callback(Output('kafka_broker_title', 'children'), [Input('input_kafka_broker', 'value')])
    def update_kafka_broker_title(kafka_broker):
        if kafka_broker is None:
            raise PreventUpdate
        return "kafka broker: "+kafka_broker

    @app.callback(
        Output('launching-producer-text-display', 'children'),
        [Input('treemap', 'clickData')], [State("input_kafka_broker", "value"), State('treemap', 'figure')])
    def treemap(clickData, kafka_broker, figure):
        if clickData is None:
            raise PreventUpdate

        data = clickData['points'][0]

        if not 'currentPath' in data:
            raise PreventUpdate

        parents = figure['data'][0]['parents']

        # selected elemenent is not a leaf (i.e. file) or we dont have a kafka broker specified
        if data['label'] in parents or kafka_broker is None:
            raise PreventUpdate

        filename = data['currentPath']+'/'+data['label']
        error = launchProducer(kafka_broker, filename)

        if error == Error.NO_ERROR:
            return "Produced: "+filename
        return "Status: "+ErrorToString[error]

    @app.callback(Output('topics-table', 'data'),
                  [Input('interval-component', 'n_intervals')],
                  [State('input_kafka_broker', 'value')]
                  )
    def update_list_topics(n_intervals, kafka_broker):
        topics = get_topics(kafka_broker)
        if topics[0] != Error.NO_ERROR:
            raise PreventUpdate

        return [{"topics": x} for x in topics[1]]

    app.run_server(debug=True)
