import os
import ast
import time
import pystache

from kubernetes import client as k_client
from kubernetes import config as k_config
from kubernetes.client.rest import ApiException


class ComputeParty:

    def __init__(self, pid, all_pids, timestamp, protocol):

        self.template_directory = "{}/templates/".format(os.path.dirname(os.path.realpath(__file__)))
        self.pid = pid
        self.all_pids = all_pids
        self.timestamp = timestamp

        self.name = "conclave-{0}-{1}".format(timestamp, str(pid))
        self.config_map_name = "conclave-{0}-{1}-map".format(timestamp, str(pid))

        self.protocol = protocol
        self.conclave_config = self.gen_net_config()
        self.config_map_body = self.define_config_map()
        self.pod_body = self.define_pod()
        self.service_body = self.define_service()

    def gen_conclave_config(self):

        net_str = self.gen_net_config()

        params = \
            {
                "PID": self.pid,
                "ALL_PIDS": ", ".join(i for i in self.all_pids),
                "WORKFLOW_NAME": "conclave-{}".format(self.timestamp),
                "NET_CONFIG": net_str
            }

        data_template = open("{}/conclave_config.tmpl".format(self.template_directory), 'r').read()

        return pystache.render(data_template, params)

    def gen_net_config(self):

        net_str = ""

        for i in self.all_pids:
            if i == self.pid:
                net_str += "\t\t-host: 0.0.0.0\n\t\tport: 5000\n"
            else:
                net_str += "\t\t-host: {0}-{1}\n\t\tport: 5000\n".format(self.timestamp, str(i))

        return net_str

    def define_config_map(self):

        data_params = \
            {
                "PROTOCOL": self.protocol,
                "CONF": self.conclave_config
            }

        data_template = "{}/configmap_data.tmpl".format(self.template_directory)

        return ast.literal_eval(pystache.render(data_template, data_params))

    def define_pod(self):

        params = \
            {
                "POD_NAME": self.name,
                "CONFIGMAP_NAME": self.config_map_name
            }

        data_template = open("{}/pod.tmpl".format(self.template_directory), 'r').read()

        self.pod_body = ast.literal_eval(pystache.render(data_template, params))

        return self

    def define_service(self):

        params = \
            {
                "SERVICE_NAME": self.name
            }

        data_template = open("{}/service.tmpl".format(self.template_directory), 'r').read()

        self.service_body = ast.literal_eval(pystache.render(data_template, params))

        return self

    def launch(self):

        k_config.load_incluster_config()
        kube_client = k_client.CoreV1Api()
        kube_batch_client = k_client.BatchV1Api()

        configmap_metadata = k_client.V1ObjectMeta(name=self.config_map_name)
        configmap_body = k_client.V1ConfigMap(data=self.config_map_body, metadata=configmap_metadata)
        print("ConfigMap: {}".format(configmap_body))

        try:
            api_response = kube_client.create_namespaced_config_map('cici', configmap_body, pretty='true')
            print("Namespace created successfully with response {}\n".format(api_response))
        except ApiException as e:
            print("Exception: {}".format(e))

        # TODO: launch service & pod

        return


class ConclaveManager:

    def __init__(self, json_data):

        self.template_directory = "{}/templates/".format(os.path.dirname(os.path.realpath(__file__)))
        self.protocol_config = json_data  # request.get_json(force=True)

        self.protocol = self.load_protocol()
        self.compute_parties = None

    def load_protocol(self):
        """
        Will later load this from self.protocol_config.protocol
        """

        mock_data_directory = "{}/mock_data".format(os.path.dirname(os.path.realpath(__file__)))
        self.protocol = open("{}/protocol.py".format(mock_data_directory)).read()

        return self

    def create_compute_parties(self):
        """
        
        """

        timestamp = str(int(round(time.time() * 1000)))
        all_pids = list(range(1, len(self.protocol_config.dataRows) + 1))
        compute_parties = []

        for i in all_pids:
            compute_parties.append(ComputeParty(i, all_pids, timestamp, self.protocol))

        self.compute_parties = compute_parties

        return self

    def launch_all_parties(self):
        """
        Create ConfigMap, Services, and Pod for each compute party & launch
        """

        if self.compute_parties is None:
            self.create_compute_parties()

        for party in self.compute_parties:
            party.launch()





