import json
import requests
from requests.auth import HTTPBasicAuth
import os

urlquery = "http://127.0.0.1:8000/api/query-lenses-full/"
ra, dec = 260.45419, 88.70621

search_field_values =  {'lens-ra_min': '0', 'lens-ra_max': '360', 'lens-dec_min': '-90', 'lens-dec_max': '0', #box search
                        #'lens-ra_centre': '0', 'lens-dec_centre': '1', 'lens-radius': '0.001', #cone search
                        #'lens-n_img_min': '5', 'lens-n_img_max': '6', #number of images
                        #'lens-image_sep_min': '7', 'lens-image_sep_max': '8', #image separation
                        'lens-score_min': '1.5', 'lens-score_max': '3', #score for candidates
                        'lens-flag': ['CANDIDATE',], #flag for confirmed, candidate or contamiant systems
                        #'lens-lens_type': 'GALAXY', #lens type, options are: ['GALAXY', 'LTG', 'SPIRAL', 'GALAXY PAIR', 'GROUP', 'CLUSTER', 'CLUSTER MEMBER', 'QUASAR', 'LRG', 'ETG', 'ELG']
                        'lens-source_type': ['QUASAR',], #lens source type, options are: ['GALAXY', 'ETG', 'SMG', 'QUASAR', 'DLA', 'PDLA', 'RADIO-LOUD', 'BAL QUASAR', 'ULIRG', 'BL Lac', 'LOBAL QUASAR', 'FELOBAL QUASAR', 'EXTREME RED OBJECT', 'RED QUASAR', 'GW', 'FRB', 'GRB', 'SN', 'LBG', 'ETG', 'ELG']
                        #'lens-image_conf': 'LONG-AXIS CUSP', 'SHORT-AXIS CUSP', 'NAKED CUSP', 'CUSP', 'CENTRAL IMAGE', 'FOLD', 'CROSS', 'DOUBLE', 'QUAD', 'RING', 'ARC',
                        #'redshift-z_lens_method': '', 'redshift-z_lens_min': '', 'redshift-z_lens_max': '', options are "leave it blank for ANY", 'PHOTO', 'SPECTRO', 'OTHER'
                        #'redshift-z_source_method': '', 'redshift-z_source_min': '', 'redshift-z_source_max': '', options are "leave it blank for ANY", 'PHOTO', 'SPECTRO', 'OTHER'
                        #'redshift-z_los_method': '', 'redshift-z_los_min': '', 'redshift-z_los_max': '', options are "leave it blank for ANY", 'PHOTO', 'SPECTRO', 'OTHER'
                        #'imaging-band': '', 'imaging-future': '', #for imaging band numbers check the curl request: ['2', '6', '5', '1']
                        #'imaging-date_taken_min_month': '', 'imaging-date_taken_min_day': '', 'imaging-date_taken_min_year': '',
                        #'imaging-date_taken_max_month': '', 'imaging-date_taken_max_day': '', 'imaging-date_taken_max_year': '',
                        #'imaging-exposure_time_min': '', 'imaging-exposure_time_max': '',
                        #'imaging-pixel_size_min': '', 'imaging-pixel_size_max': '',
                        #'spectrum-future': '',
                        #'spectrum-date_taken_min_month': '', 'spectrum-date_taken_min_day': '', 'spectrum-date_taken_min_year': '',
                        #'spectrum-date_taken_max_month': '', 'spectrum-date_taken_max_day': '', 'spectrum-date_taken_max_year': '',
                        #'spectrum-exposure_time_min': '', 'spectrum-exposure_time_max': '',
                        #'spectrum-wavelength_min': '', 'spectrum-wavelength_max': '',
                        #'spectrum-resolution_min': '', 'spectrum-resolution_max': '',
                        #'catalogue-band': '', 'catalogue-future': '',
                        #'catalogue-date_taken_min_month': '', 'catalogue-date_taken_min_day': '', 'catalogue-date_taken_min_year': '',
                        #'catalogue-date_taken_max_month': '', 'catalogue-date_taken_max_day': '', 'catalogue-date_taken_max_year': '',
                        #'catalogue-distance_min': '', 'catalogue-distance_max': '',
                        #'catalogue-mag_min': '', 'catalogue-mag_max': '',
                    }

urlquery = "http://127.0.0.1:8000/api/query-lenses-full/"
username, password = os.getenv('SLED_USERNAME'), os.getenv('SLED_PASSWORD')

if (not username) or (not password):
    print('You have not set your SLED username and password environment variables. Please read the comments above.')
r = requests.post(urlquery, data=search_field_values, auth=HTTPBasicAuth(username, password))
dbquery = json.loads(r.text)

if dbquery['errors']:
    print('ERROR with INPUT:', dbquery['errors'])
else:
    lenses = dbquery['lenses']
    if len(lenses) == 0:
        print('No lenses found')
    else:
        print('Found '+str(len(lenses))+ ' lenses:')

