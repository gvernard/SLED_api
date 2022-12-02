import json                    
import requests
from requests.auth import HTTPBasicAuth

import os
import sys

# Specify the URL for the request to be sent
url = "http://127.0.0.1:8000/api/query-lenses/"

data = {'ra':2.834350, 'dec':-8.764070, 'radius':3.}

# Sending the request
r = requests.post(url, data=data, auth=HTTPBasicAuth('Cameron','123')) #, headers={'Accept': 'application/json', 'Content-Type': 'application/json'})

# Printing the response of the request
if r.ok:
    print("Query completed successfully!")
print(r.text)


