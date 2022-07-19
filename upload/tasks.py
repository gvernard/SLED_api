# main/tasks.py
 
import logging
 
from django.urls import reverse
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from mysite.celery import app
from lenses.models import *
import os
import urllib.request
import astropy.io.fits as fits
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matt_colorImage as ma_colorImage
import numpy as np
import panstarrs as ps

from astropy.table import Table

from astroquery.sdss import SDSS
from astroquery.vizier import Vizier
import astropy.units as u
import astropy.coordinates as coord


import os
import json
from astropy.table import Table

import panstarrs_utils
import legacysurvey_utils
import imaging_utils
import database_utils


import sys
sys.path.append('../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django
django.setup()

from django.conf import settings
from lenses.models import Imaging, Spectrum, Instrument, Band, Users, Lenses
from api.serializers import ImagingDataUploadSerializer
from django.db.models import Q, F, Func, FloatField, CheckConstraint


'''
the decorator @app.task tells celery this is a task and will be run in the task queue
'''

@app.task
def get_imaging(name, ra, dec, survey='PanSTARRS', bands='grizY', instrument='Pan-STARRS1'):
    outpath = str(settings.BASE_DIR)+'/data/images_to_upload/'
    jsonpath = outpath+'jsons/'
    imagepath = outpath+'images/'
    verbose = True
    username, password = 'admin', '123'
    uploads = []
    for band in bands:
        jsonfile = jsonpath+name+'_'+survey+'_'+band+'.json'
        if verbose:
            print('checking for ', survey,' data in', band)
        #download the PanSTARRS data
        if survey=='PanSTARRS':
            datafile = panstarrs_utils.panstarrs_data(name, ra, dec, band, outpath=jsonpath, size=10, verbose=verbose)
        elif survey=='LegacySurveySouth':
            datafile = legacysurvey_utils.legacysurvey_data(name, ra, dec, band, layer='ls-dr9-south', outpath=jsonpath, size=10, verbose=verbose)
        elif survey=='LegacySurveyNorth':
            datafile = legacysurvey_utils.legacysurvey_data(name, ra, dec, band, layer='ls-dr9-north', outpath=jsonpath, size=10, verbose=verbose)
        

        #if the data exists, create the json and image for upload
        if datafile is not None:
            if survey=='PanSTARRS':
                jsonfile = panstarrs_utils.panstarrs_band_image_and_json(name=name, ra=ra, dec=dec, band=band, jsonpath=jsonpath, imagepath=imagepath)
            elif survey=='LegacySurveySouth':
                jsonfile = legacysurvey_utils.legacy_survey_layer_band_image_and_json(name, ra, dec, band, layer='ls-dr9-south', jsonpath=jsonpath, imagepath=imagepath, size=10)
            elif survey=='LegacySurveyNorth':
                jsonfile = legacysurvey_utils.legacy_survey_layer_band_image_and_json(name, ra, dec, band, layer='ls-dr9-north', jsonpath=jsonpath, imagepath=imagepath, size=10)
            

            f = open(jsonfile)
            uploadjson = json.load(f)
            f.close()

            uploads.append(uploadjson)
            #now upload it
            #upload = upload_imaging_to_db_API(data=uploadjson)

        #if the data does not exist, then upload an exists=False json so we know not to try again (DIRECT ONLY)
        if datafile is None:
            uploadjson = imaging_utils.checked_and_nodata_json(jsonfile, name, ra, dec, band, instrument=instrument)
            uploads.append(uploadjson)

    upload = database_utils.upload_imaging_to_db_direct(datalist=uploads, username=username)
