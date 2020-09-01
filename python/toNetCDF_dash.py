#!/usr/bin/python3
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import argparse
import sd_material_ui
import toNetCDF as tonetcdf
import random
import string
import pathlib
import json
import subprocess
import os

app = dash.Dash()
verbose = False


def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def subscribeOutputProducts(kafka_broker, product, s3bucket):

    configfilename = "toNetCDF.yaml"

    jdata = {}
    jdata['kafkabroker'] = kafka_broker
    jdata['product'] = product
    jdata['s3bucket'] = s3bucket
    jdata['default'] = {}
    jdata['default']['fields'] = {}
    jdata['default']['fields']['.*'] = {}
    jdata['default']['fields']['.*']["desc"] = "3d"

    cdir = pathlib.Path(__file__).parent.absolute()
    tmpdir = cdir / pathlib.Path('tmpdash___')

    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)

    filenameflat = pathlib.Path(product+get_random_string(4))

    tconfig = tmpdir / filenameflat.with_suffix(".configtmp.json")
    with open(tconfig, "w") as jfile:
        json.dump(jdata, jfile)

    tonetcdf.outputProducts(tconfig)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='toNetCDF_dash.py')
    parser.add_argument(
        '-v', help='run in debug mode', action="store_true")

    args = parser.parse_args()

    if args.v:
        verbose = True

    app.layout = html.Div([
        html.Div([
            html.Div(id="kafka_title", children="kafka broker"),
            dcc.Input(
                id="input_kafka_broker".format("text"),
                type="text",
                placeholder="kafka broker".format("text"),
            ),
            html.Div(id="kafka_broker_title"),
            html.Div(id="s3_bucket_title", children="s3 bucket"),
            dcc.Input(
                id="input_s3_bucket".format("text"),
                type="text",
                placeholder="s3 bucket".format("text"),
            ),
            html.Div(id="product_prefix_title", children="product prefix"),

            html.Div([
                dcc.Input(
                    id="input_product_prefix".format("text"),
                    type="text",
                    placeholder="product prefix".format("text"),
                ),
            ]),
            html.Button(id='submit-buttom',
                        n_clicks=0, children='Submit'),

            sd_material_ui.Snackbar(
                id='snackbar-submit-io', open=False, message='')
        ]),
    ])

    @app.callback([dash.dependencies.Output('snackbar-submit-io', 'open'),
                   dash.dependencies.Output('snackbar-submit-io', 'message')],
                  [Input('submit-buttom', 'n_clicks')], [State('input_kafka_broker', 'value'),
                                                         State('input_product_prefix', 'value'), State('input_s3_bucket', 'value')])
    def subscribe_an_output_product(n_clicks, kafka_broker, product_prefix, s3bucket):
        if n_clicks <= 0:
            raise PreventUpdate

        subscribeOutputProducts(kafka_broker, product_prefix, s3bucket)
        return True, "recording kafa products, "+product_prefix+" into s3 bucket: "+s3bucket

    app.run_server(debug=True, host='0.0.0.0', port=3000)
