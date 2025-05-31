import requests 
import json

response = requests.post(
    'http://localhost:8888/ask' , 
    json = {
        'query' : 'Hey' , 
        'session_id' : 'wedsf'
    }
)

print(json.dumps(response.json() , indent = 4))