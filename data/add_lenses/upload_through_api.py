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
urlquery = "http://127.0.0.1:8000/api/query-lenses/"
urlupdatelens = "http://127.0.0.1:8000/api/update-lens/"
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

        #CHECK IF LENS ALREADY EXISTS
        
        lensdata = {'ra':lens_dict['ra'], 'dec':lens_dict['dec'], 'radius':3.}
        r = requests.post(urlquery, data=lensdata, auth=HTTPBasicAuth('Cameron','123'))
        dbquery = json.loads(r.text)
        dblenses = dbquery['lenses']
        if len(dblenses)>0:
            dblens = dblenses[0]
            print('EXISTING LENS!')
            print('CHECKING FOR UPDATED FIELDS')
            update_data = {'ra':dblens['ra'], 'dec':dblens['dec']}
            send_update = False

            #CONSTRUCT UPDATE PARAMETER LIST
            for field in dblens.keys():
                #ONLY UPDATE FIELDS THAT ARE GIVEN
                if (field in lens_dict.keys()):
                    #AND ARE NOT EMPTY
                    if lens_dict[field]!='':
                        value = lens_dict[field]
                        if (value=='') & (field!='info'):
                            value = None
                        if (value==None)&(field=='z_lens_secure'):
                            value = False
                        if field in ['image_conf', 'lens_type', 'source_type']:
                            if value!=None:
                                value = [x.strip() for x in value.split(',')]
                            else:
                                value = []
                        if value!=dblens[field]:
                            send_update = True
                            print(field)
                            print('new value', value)
                            print('old value', dblens[field])
                            if (field=='name')&(lens_dict['flag_discovery']):
                                print('Would you like to add this name and the current name to the alternative names list? And change the name to J...')
                                answer = input()
                                if answer.lower()=='y':
                                    oldname = dblens['name']
                                    for i, character in enumerate(oldname):
                                        if character.isdigit():
                                            break
                                    newname = 'J'+oldname[i:]
                                    if dblens['alt_name']:
                                        altname = dblens['alt_name']+', '+oldname
                                    else:
                                        altname = oldname+', '+lens_dict['name']

                                    update_data['name'] = newname
                                    update_data['alt_name'] = altname
                            else:
                                update_data[field] = lens_dict[field]
                                

            if send_update:
                r = requests.post(urlupdatelens, json=update_data, auth=HTTPBasicAuth('Cameron','123'))
                print(r.text)
                #wait = input()

        else:
            lens_dicts.append(lens_dict)

    form_data = lens_dicts
    if len(form_data)==0:
        continue
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
            print("Something went wrong!")
            wait = input()
            print('d///f')
    


