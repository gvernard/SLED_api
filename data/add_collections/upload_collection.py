import json                    
import requests
from requests.auth import HTTPBasicAuth
import glob

# Specify the URL for the request to be sent
url = "http://127.0.0.1:8000/api/upload-collection/"

# Specify the json file with the papers' properties
collections = glob.glob('./jsons/*json')


for collection_json in collections:
    # Opening the JSON file with the lens properties
    f = open(collection_json)
    data = json.load(f)
    f.close()


    # Sending the request
    r = requests.post(url,json=data,auth=HTTPBasicAuth('admin','123'))


    # Printing the response of the request
    if r.ok:
        print("Upload completed successfully!")
    else:
        print("Something went wrong!")
    print(r.text)
