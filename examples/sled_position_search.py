import json
import requests
from requests.auth import HTTPBasicAuth

urlquery = "http://127.0.0.1:8000/api/query-lenses/"
ra, dec = 260.45419, 88.70621

lensdata = {'ra':ra, 'dec':dec, 'radius':10.}
r = requests.post(urlquery, data=lensdata, auth=HTTPBasicAuth(username, password))
dbquery = json.loads(r.text)

