import json                    
import requests
from requests.auth import HTTPBasicAuth


# Specify the URL for the request to be sent
url = "http://127.0.0.1:8000/api/upload-lenses/"

# Specify the directory where the mugshot for each lens is found
mugshot_dir = "lens_mugshots/"

# Specify the json file with the lens properties
lenses_json_file = 'lenses_to_upload.json'



# Opening the JSON file with the lens properties
f = open(lenses_json_file)
lenses = json.load(f)
f.close()


form_data = [
    ('N', ('',str(len(lenses)))),
    ('ra', ('',str(lenses[0]['ra']))),
    ('dec', ('',str(lenses[0]['dec']))),
    ('mugshot', open(mugshot_dir + lenses[0]["mugshot"],"rb")),
    ('ra', ('',str(lenses[1]['ra']))),
    ('dec', ('',str(lenses[1]['dec']))),
    ('mugshot', open(mugshot_dir + lenses[1]["mugshot"],"rb"))
]
print(form_data)


# Sending the request
r = requests.post(url,files=form_data,auth=HTTPBasicAuth('gvernard','123'))

# Printing the response of the request
if r.ok:
    print("Upload completed successfully!")
else:
    print("Something went wrong!")
print(r.text)
