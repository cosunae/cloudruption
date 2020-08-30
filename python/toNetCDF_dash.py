import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import argparse
import sd_material_ui
import toNetCDF as tonetcdf

app = dash.Dash()
verbose = False

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


def launchProducer(kafka_broker):

    # test valid broker, it will throw in case of invalid broker
    topics = get_topics(kafka_broker)

    cdir = pathlib.Path(__file__).parent.absolute()
    tmpdir = cdir / pathlib.Path('tmpdash___')
    if not pathlib.Path(tmpdir).exists():
        os.mkdir(tmpdir)
    lockf = tmpdir / filenameflat.with_suffix(".rlock")

    # Can not acquire lock
    if pathlib.Path(lockf).exists():
        raise Exception(
            "Can not acquier lock to produce file, another process already running")

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
    jdata['product'] = "pp"

    tconfig = tmpdir / filenameflat.with_suffix(".configtmp.json")
    jfile = open(tconfig, "w")
    json.dump(jdata, jfile)
    jfile.close()

    res = subprocess.run([producer, tconfig], check=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if verbose:
        print('stdout:', res.stdout)
        print('stderr:', res.stderr)

    @app.callback([dash.dependencies.Output('snackbar-submit-io', 'open'),
                   dash.dependencies.Output('snackbar-submit-io', 'message')],
                  [Input('submit-buttom', 'n_clicks')], [State('input_kafka_broker', 'value'),
                                                         State('input_product_prefix', 'value'), State('input_s3_bucket', 'value')])
    def delete_topics_cb(n_clicks, kafka_broker, product_prefix, s3bucket):
        try:
            topics_to_be_deleted = delete_kafka_topics(kafka_broker, regex)
        except Exception as ex:
            print(ex)
            raise PreventUpdate

        return True, "recording kafa products, "+product_prefix+" into s3 bucket: "+s3bucket

    app.run_server(debug=True, host='0.0.0.0', port=3000)
