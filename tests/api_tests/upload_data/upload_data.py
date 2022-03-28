import json                    
import requests
from requests.auth import HTTPBasicAuth


# Specify the URL for the request to be sent
url = "http://127.0.0.1:8000/api/upload-data/"

# Specify the directory where the mugshot for each lens is found
data_dir = "lens_data/"

# Specify the json file with the lens properties
data_json_file = 'data_to_upload.json'


# Opening the JSON file with the lens properties
f = open(data_json_file)
data = json.load(f)
f.close()


form_data = [
   ('N', ('',str(len(data)))),
   ('type', ('','Imaging'))
]
for datum in data:
   dum = []
   for key in datum.keys():
      if key != 'image':
         dum.append( (key,('',str(datum[key]))) )
      else:
         dum.append( ('image',open(data_dir + datum[key],'rb')) )
   form_data.extend(dum)
#print(form_data)
                     
    
# Sending the request
r = requests.post(url,files=form_data,auth=HTTPBasicAuth('gvernard','123'))


# Printing the response of the request
if r.ok:
    print("Upload completed successfully!")
else:
    print("Something went wrong!")
print(r.text)
