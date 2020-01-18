#!/bin/bash

gcloud container clusters create kubecluster
gcloud container clusters get-credentials kubecluster
kubectl apply -f container_manifest.yaml
