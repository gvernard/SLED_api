import json                    
import requests
from requests.auth import HTTPBasicAuth


# Specify the URL for the request to be sent
url = "http://127.0.0.1:8000/api/upload-collection/"

# Specify the json file with the papers' properties
papers_json_file = 'collection.json'
papers_json_file = 'H0LiCOW.json'
papers_json_file = 'CLASS.json'


# Opening the JSON file with the lens properties
f = open(papers_json_file)
data = json.load(f)
f.close()


# Sending the request
r = requests.post(url,json=data,auth=HTTPBasicAuth('Cameron','123'))


# Printing the response of the request
if r.ok:
    print("Upload completed successfully!")
else:
    print("Something went wrong!")
print(r.text)
