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

outpath='../images_to_upload/'
jsonpath = outpath+'jsons/'
imagepath = outpath+'images/'
verbose = True
username, password = 'admin', '123'

surveys = ['PanSTARRS', 'LegacySurveySouth', 'LegacySurveyNorth']
bandss = ['grizY', 'grz', 'grz']
instruments = ['Pan-STARRS1', 'Legacy Survey (South)', 'Legacy Survey (North)']
for kk in range(len(surveys)):
    survey, bands, instrument = surveys[kk], bandss[kk], instruments[kk]

    uploads = []
    lenses = Lenses.objects.all()
    for lens in lenses:
        #see whether spectra exist for this lens
        allimaging = Imaging.objects.all().filter(lens=lens).filter(instrument__name=instrument)
        if len(allimaging)==0:
            print('No images have been checked for', lens.name)

            name, ra, dec = lens.name, lens.ra, lens.dec
            ra = float('{0:.4f}'.format(ra))
            dec = float('{0:.4f}'.format(dec))
           
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
