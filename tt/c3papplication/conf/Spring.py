from flask import Flask
from jproperties import Properties
import json

app = Flask(__name__)

data = {}
configs = Properties()
name = 'C3Ppcore-local.properties'
with open(name, 'rb') as config_file:
    configs.load(config_file)
data['propertySources'] = [{'name': name, 'source': {k: v.data for k, v in configs.items()}}]
    

@app.route('/C3Ppcore/<profile>')
def serve_config(profile):
    print(profile)
    return json.dumps(data)

if __name__ == '__main__':
    host = 'localhost'
    port = 8888
    app.run(host=host, port=port, debug=False)