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
sys.path.append('../add_data/')
import panstarrs_utils
import legacysurvey_utils
import glob

download_missing_images_from_panstarrs_or_des = True

# Specify the URL for the request to be sent
url = "http://127.0.0.1:8000/api/upload-lenses/"

# Specify the directory where the mugshot for each lens is found
mugshot_dir = "../images_to_upload/initial_mugshots/"
csv_dir = "csvs/"



#image_files = []
csvs = np.sort(glob.glob(csv_dir+'*.csv'))

for eachcsv in csvs:
    print(eachcsv)
    lens_dicts = []
    data = pd.read_csv(eachcsv, skipinitialspace=True)

    #this deals with nans where you have empty entries
    data = data.fillna({key:(False if 'flag' in key else '') for key in data.keys()})
    for i in range(len(data)):

        lens_dict = data.iloc[i].to_dict()
        #print(lens_dict)
        #image = Image.open(mugshot_dir+lens_dict['imagename'])
        if lens_dict['imagename']=='':
            lens_dict['imagename'] = lens_dict['name'].split(',')[0].strip()+'.png'
        #if os.path.exists(mugshot_dir+lens_dict['imagename']):
        #    os.system('rm '+mugshot_dir+lens_dict['imagename'])
        if not os.path.exists(mugshot_dir+lens_dict['imagename']):
            print('The following mugshot does not exist:', mugshot_dir+lens_dict['imagename'])

            if download_missing_images_from_panstarrs_or_des:
                print('Querying PS to make it')
                try:
                    print('trying panstarrs with ra, dec', lens_dict['ra'], lens_dict['dec'])
                    panstarrs_utils.savecolorim(ra=lens_dict['ra'], dec=lens_dict['dec'], arcsec_width=10, outpath=mugshot_dir+lens_dict['imagename'])
                except Exception:
                    try:
                        legacysurvey_utils.savecolorim(ra=lens_dict['ra'], dec=lens_dict['dec'], arcsec_width=10, outpath=mugshot_dir+lens_dict['imagename'])
                    except Exception:
                        pass

        img = cv2.imread(mugshot_dir+lens_dict['imagename'])
        string_img = base64.b64encode(cv2.imencode('.jpg', img)[1]).decode()
        lens_dict['mugshot'] = string_img 
        #image_files.append(open(mugshot_dir+lens_dict['imagename'], "rb"))
        lens_dicts.append(lens_dict)

    form_data = lens_dicts

    '''form_data = [
        ('N', ('',str(len(lenses)))),
        ('ra', ('',str(lenses[0]['ra']))),
        ('dec', ('',str(lenses[0]['dec']))),
        ('mugshot', open(mugshot_dir + lenses[0]["mugshot"],"rb")),
        ('ra', ('',str(lenses[1]['ra']))),
        ('dec', ('',str(lenses[1]['dec']))),
        ('mugshot', open(mugshot_dir + lenses[1]["mugshot"],"rb"))
    ]
    print(form_data)'''
    #files = [('json', (None, json.dumps(lens_dicts[0]), 'application/json')),
    #         ('media', (image_files[0]))]

    # Sending the request
    r = requests.post(url, json=form_data, auth=HTTPBasicAuth('Cameron','123')) #, headers={'Accept': 'application/json', 'Content-Type': 'application/json'})

    # Printing the response of the request
    if r.ok:
        print("Upload completed successfully!")
    else:
        print(r.text)
        if 'duplicates' in r.text:
            #print("Something went wrong!")
            wait = input()
    


