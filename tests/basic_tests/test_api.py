import json                    
import requests
from requests.auth import HTTPBasicAuth


r = requests.get(url='http://127.0.0.1:8000/api/global-search/',
                 params={'q':'ame'},
                 auth=HTTPBasicAuth('Giorgos','123'))
print(r.json())
