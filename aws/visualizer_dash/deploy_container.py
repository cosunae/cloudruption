#/usr/bin/python3.7
import sys
import boto3
import json

if sys.version_info[0] != 3 or sys.version_info[1] < 7:
    print("This script requires Python version 3.7")
    sys.exit(1)

import subprocess
import argparse

def list_tags():
  print("Listing AWS ECR images")
  client = boto3.client('ecr')
  print(json.dumps(client.list_images(repositoryName="cr-visualizer"), sort_keys=True, indent=2))
  pass

def tag_image(tag):
  out = subprocess.run(['docker', 'build','-q','.'],capture_output=True)
  if out.returncode != 0:
    raise RuntimeError("docker build failed")
  
  hashtag = out.stdout.decode("utf-8").strip()
  
  print("Docker hash image:", hashtag)
  cmd = ['docker','tag',hashtag,'066650776666.dkr.ecr.eu-central-1.amazonaws.com/cr-visualizer:'+tag]
  print(cmd)
  out = subprocess.run(cmd, capture_output=True)
  
  if out.returncode != 0:
    raise RuntimeError("docker tag failed")
 
  print("push docker image")
  cmd=['docker','push','066650776666.dkr.ecr.eu-central-1.amazonaws.com/cr-visualizer:'+tag]
  print(cmd) 
  out = subprocess.run(['docker','push','066650776666.dkr.ecr.eu-central-1.amazonaws.com/cr-visualizer:'+tag], capture_output=True)
  
  if out.returncode != 0:
    raise RuntimeError("docker push failed")
 
if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument(
        '--tag', help='tag of image')
  parser.add_argument(
        '--list_tags', help='list tags in AWS ECR',action='store_true')

  args = parser.parse_args()
  
  if args.list_tags:
    list_tags()

  else:
    if not args.tag:
      raise RuntimeError("--tag not especified")
    tag_image(args.tag)

 
