import os

from flask import Flask
from flask import request
from flask import render_template
from kubernetes import client as k_client
from openshift import client as o_client
import yaml
import json
import os
from openshift import config
from kubernetes.client.rest import ApiException



app = Flask(__name__)



@app.route("/")
def index():
    return render_template('hello.html')

@app.route('/login', methods=['POST'])
def login():
    kubecfg_path = os.environ.get('KUBECFG_PATH')
    config.load_kube_config(config_file='/tmp/.kube/kube-config')
    # if kubecfg_path is None:
    #     config.load_kube_config()
    # else:
    #     config.load_kube_config(config_file=kubecfg_path)
    print ('config: ',config)
    openshift_client = o_client.OapiApi()
    kube_client = k_client.CoreV1Api()
    kube_v1_batch_client = k_client.BatchV1Api()

    print ('kube_client: ',kube_client)
    print ('kube_v1_batch_client: ',kube_v1_batch_client)


    if request.method == 'POST':
        content = request.json
        print ('from json:  ',content['mytext'])
        name='conclavepy'
        # image='docker.io/singhp11/pyspark-python3'
        image='docker.io/singhp11/python3-hello-world'

        d_job = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": name
            },
            "spec": {
                "parallelism": 1,
                "completions": 1,
                "activeDeadlineSeconds": 3600,
                "template": {
                    "metadata": {
                        "name": name
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": name,
                                "image": image,
                                # "env": [
                                #
                                #     {
                                #         "name": "KUBECFG_PATH",
                                #         "value": "/tmp/.kube/config"
                                #     },
                                #     {
                                #         "name": "OPENSHIFTMGR_PROJECT",
                                #         "value": "cici"
                                #     }
                                # ],
                                "command": [
                                    "python",
                                    "/opt/app-root/app.py"
                                ],
                                "volumeMounts": [

                                    {
                                        "name": "kubecfg-volume",
                                        "mountPath": "/tmp/.kube/",
                                        "readOnly": True
                                    },
                                ]

                                # "volumeMounts": [
                                #     {
                                #         "name": "config-volume",
                                #         "mountPath": "/etc/config"
                                #     }
                                # ]
                            }
                        ]
                    }
                }
            }
        }
        d_job['spec']['template']['spec']['volumes'] = [

            {
                "name": "kubecfg-volume",
                "secret": {
                    "secretName": "kubecfg"
                }
            }
        ]


        project = os.environ.get('OPENSHIFTMGR_PROJECT') or 'cici'
        print ('Namespace: ', project)
        try:
            api_response = kube_client.list_namespaced_pod(project)
            print('****************: ',api_response)
        except ApiException as e:
            print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)
        job = kube_v1_batch_client.create_namespaced_job(namespace=project, body=d_job)


        return render_template('submit.html')





if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)