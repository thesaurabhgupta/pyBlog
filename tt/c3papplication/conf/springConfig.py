import requests

class springConfig:

    def __init__(self) -> None:
        # local Environment
        # self.host = 'localhost'
        # self.profile = 'local'
        # VM Environment
        self.host = '10.179.128.54'
        # self.host = 'c3p-j-cloudconfigserver-service.c3pdev.svc.cluster.local'
        self.profile = 'dev'
        # self.url = f'http://{self.host}:8888/C3Ppcore/{self.profile}'
        self.url = f'http://{self.host}/C3Ppcore/{self.profile}'

    def fetch_config(self):
        data = requests.get(self.url).json()
        properties = {}
        for source in data.get('propertySources', []):
            if f'{self.profile}.properties' in source['name'] and source.get('source'):
                properties = source['source']
                break

        return properties
