import json
from orthanc_helper import Server

with open('config.json', 'r') as config:
    data = json.load(config)

SERVER_URL = data['server']['url']
USERNAME = data['server']['username']
PASSWORD = data['server']['password']

orthanc = Server(SERVER_URL, USERNAME, PASSWORD)
orthanc.upload("~/Documents/Test")