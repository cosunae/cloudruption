import argparse
import subprocess, sys
import tempfile
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='consumer')
    parser.add_argument('--kafkabroker', help='IP of kafka broker')
    parser.add_argument('--exe', required=True, help='path to consumer executable')

    args = parser.parse_args()

    with open('config.json', 'r+') as f:
        data = json.load(f)
        if args.kafkabroker:
            data["kafkabroker"] = args.kafkabroker
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()

    subprocess.run(args.exe)