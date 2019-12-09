#!/bin/bash

gcloud container clusters create kubecluter
gcloud container clusters get-credentials kubecluster
kubeflow apply -f container_manifest.yaml
