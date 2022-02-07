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
data_lenses = {'lenses':json.dumps(lenses)}


# Creating a dict with the images
mugshot_files = {}
for lens in lenses:
    mugshot_files[lens["mugshot"]] = open(mugshot_dir + lens["mugshot"], "rb")

    
# Sending the request 
r = requests.post(url,files=mugshot_files,data=data_lenses,auth = HTTPBasicAuth('gvernard','123'))


# Printing the response of the request
if r.ok:
    print("Upload completed successfully!")
else:
    print("Something went wrong!")
print(r.text)
