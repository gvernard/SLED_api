import json                    
import requests
from requests.auth import HTTPBasicAuth
#import csv
import pandas as pd
#from PIL import Image
import numpy as np
import cv2
import base64
import os
import sys
import glob

# Specify the URL for the request to be sent
url = "http://127.0.0.1:8000/api/upload-papers/"

# Specify the directory where the mugshot for each lens is found
json_dir = "csvs/"



#image_files = []
jsons = np.sort(glob.glob(json_dir+'*.json'))

for eachjson in jsons:

    f = open(eachjson)
    data = json.load(f)
    f.close()



    r = requests.post(url,json=data,auth=HTTPBasicAuth('Cameron','123'))

    # Printing the response of the request
    if r.ok:
        print("Upload completed successfully!")
    else:
        print("Something went wrong!")
        print(eachjson)
        df
    #x = input()
    #print(r.text)

