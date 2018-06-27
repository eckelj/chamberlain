import time
import logging
import os

from flask import Flask
from flask import request
from flask import render_template
from flask import jsonify
from openshift import config as o_config
from openshift import client as o_client
from kubernetes import client as k_client
from kubernetes.client.rest import ApiException
from flask_cors import CORS

app = Flask(__name__, static_folder="./dist/static", template_folder="./dist")

# CORS to allow status calls from backend to frontend
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})


if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return render_template("index.html")


@app.route('/api/job_status')
def job_status(status=None):
    """
    After querying status of Conclave job, send response to frontend.
    """

    # dummy temp response
    if status is None:
        status = 'everything ok'

    response = \
        {
            'status': status
        }

    return jsonify(response)


@app.route('/api/submit', methods=['POST'])
def submit():
    """
    TODO: how to bind service account credentials to this?
    """

    kube_client = k_client.CoreV1Api()
    kube_batch_client = k_client.BatchV1Api()

    timestamp = str(int(round(time.time() * 1000)))

    if request.method == 'POST':

        jsondata = request.get_json(force=True)
        config_data = jsondata['config']
        protocol = ["{}\n".format(item) for item in jsondata['protocol']]

        data = \
            {
                "protocol.py":  protocol,
                "config_data": config_data
            }

        configmap_name = ''.join(['conclaveweb', '-', timestamp])
        configmap_metadata = k_client.V1ObjectMeta(name=configmap_name)
        configmap_body = k_client.V1ConfigMap(data=data, metadata=configmap_metadata)

        try:
            api_response = kube_client.create_namespaced_config_map('cici', configmap_body, pretty='true')
            app.logger.info("Namespace created successfully with response {}\n".format(api_response))
        except ApiException as e:
            app.logger.error("Error creating config map: {}\n".format(e))

        name = ''.join(['conclave-web-hw', '-', timestamp])
        image = 'docker.io/singhp11/python3-hello-world'

        d_job = \
            {
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
                                    "env": [

                                        {
                                            "name": "KUBECFG_PATH",
                                            "value": "/tmp/.kube/token"
                                        },
                                        {
                                            "name": "OPENSHIFTMGR_PROJECT",
                                            "value": "cici"
                                        }
                                    ],
                                    "command": [
                                        "python",
                                        "/opt/app-root/wsgi.py"
                                    ],
                                    "volumeMounts": [
                                        {
                                            "name": "kubecfg-volume",
                                            "mountPath": "/tmp/.kube/",
                                            "readOnly": True
                                        },
                                        {
                                            "name": "config-volume",
                                            "mountPath": "/etc/config",
                                            "readOnly": True
                                        }
                                    ]
                                }
                            ],
                            "volumes": [
                                {
                                    "name": "kubecfg-volume",
                                    "secret": {
                                        "secretName": "kubecfg"
                                    }
                                },
                                {
                                    "name": "config-volume",
                                    "configMap": {
                                        "name": configmap_name
                                    }
                                }
                            ]
                        }
                    }
                }
            }

        try:
            api_response = kube_batch_client.create_namespaced_job(namespace='cici', body=d_job)
            app.logger.info("Job created with response: {}".format(api_response))
        except ApiException as e:
            app.logger.error("Exception when calling BatchV1Api->create_namespaced_job: {}\n".format(e))

        return jsonify(protocol)


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
