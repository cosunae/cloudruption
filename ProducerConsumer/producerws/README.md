
can be triggered with
curl -X POST --header 'Content-Type: application/json' --header 'Accept: text/plain' 'http://0.0.0.0:9090/v1.0/greeting/kkk'


## IN Kubernetes 
```kubectl get services```

and get the IP of producer-wms-srv

```kubectl get pods```
and get the name of pod like producer-wms-dply-6646764c49-btnfk

kubectl exec -it producer-wms-dply-6646764c49-btnfk -- sh
# curl -X POST --header 'Content-Type: application/json' --header 'Accept: text/plain' 'http://0.0.0.0:9090/v1.0/greeting/ooo'
