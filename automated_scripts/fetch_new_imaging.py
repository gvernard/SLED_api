import os
import json
from astropy.table import Table
import sys
import django
from django.conf import settings
from django.db.models import Q, F, Func, FloatField, CheckConstraint

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from lenses.models import Imaging, Spectrum, Instrument, Band, Users, Lenses
from api.serializers import ImagingDataUploadSerializer

import panstarrs_utils
import legacysurvey_utils
import imaging_utils
import database_utils
import time


outpath='../../initialize_database_data/images_to_upload/'
jsonpath = outpath+'jsons/'
imagepath = outpath+'images/'
verbose = True

upload_again = True
attempt_download = True
direct_upload = True
username, password = 'admin', '123'

lenses = Lenses.objects.all()
#for each lens we will see if the imaging data entries exist in the database, whether exists is True or False

for lens in lenses:
    panstarrs = Imaging.objects.filter(lens=lens, instrument__name='Pan-STARRS1')
    print(panstarrs)
    df

surveys = ['PanSTARRS', 'LegacySurveyDR10'] #, 'LegacySurveyNorth']
bandss = ['grizY', 'grz'] #, 'grz']
instruments = ['Pan-STARRS1', 'Legacy Survey (DR10)']#, 'Legacy Survey (North)']

#surveys = ['LegacySurveySouth', 'LegacySurveyNorth']
#bandss = ['grz', 'grz']
#instruments = ['Legacy Survey (South)', 'Legacy Survey (North)']


for kk in range(len(surveys)):
    survey, bands, instrument = surveys[kk], bandss[kk], instruments[kk]
    #for i in range(0, 50):
    for kk, lens in enumerate(lenses): 
        if (kk<Nstart) or (kk>Nend):
            continue
        print(kk, '/',len(lenses), ':', lens.name)
        uploads = []
        name, ra, dec = lens.name, float(lens.ra), float(lens.dec)
        for band in bands:
            jsonfile = jsonpath+name+'_'+survey+'_'+band+'.json'

            if (not os.path.exists(jsonfile)) & attempt_download:
                #if verbose:
                #    print('checking for ', survey,' data in', band)
                #download the PanSTARRS data

                if survey=='PanSTARRS':
                    t1 = time.time()
                    datafile = panstarrs_utils.panstarrs_data(name, ra, dec, band, outpath=jsonpath, size=10, verbose=verbose)
                    print('time to download the ps data', time.time()-t1)
                elif survey=='LegacySurveyDR10':
                    t1 = time.time()
                    datafile = legacysurvey_utils.legacysurvey_data(name, ra, dec, band, layer='ls-dr10', outpath=jsonpath, size=10, verbose=verbose)
                    print('time to download the lsdr10 data', time.time()-t1)
                #elif survey=='LegacySurveyNorth':
                #    datafile = legacysurvey_utils.legacysurvey_data(name, ra, dec, band, layer='ls-dr9-north', outpath=jsonpath, size=10, verbose=verbose)
                #    print('datafile', datafile)
                
                if datafile==0:
                    #df
                    continue
                #if the data exists, create the json and image for upload
                if datafile is not None:
                    if survey=='PanSTARRS':
                        jsonfile = panstarrs_utils.panstarrs_band_image_and_json(name=name, ra=ra, dec=dec, band=band, jsonpath=jsonpath, imagepath=imagepath)
                    elif survey=='LegacySurveyDR10':
                        t1 = time.time()
                        jsonfile = legacysurvey_utils.legacy_survey_layer_band_image_and_json(name, ra, dec, band, layer='ls-dr10', jsonpath=jsonpath, imagepath=imagepath, size=10)
                        print('time to make the legacy survey image', time.time()-t1)
                    #elif survey=='LegacySurveyNorth':
                    #    jsonfile = legacysurvey_utils.legacy_survey_layer_band_image_and_json(name, ra, dec, band, layer='ls-dr9-north', jsonpath=jsonpath, imagepath=imagepath, size=10)
                    

                    #f = open(jsonfile)
                    #uploadjson = json.load(f)
                    #f.close()

                else:
                    print('no data found for', name, instrument, band)
                    uploadjson = imaging_utils.checked_and_nodata_json(jsonfile, name, ra, dec, band, instrument=instrument)



outpath='../../initialize_database_data/images_to_upload/'
jsonpath = outpath+'jsons/'
imagepath = outpath+'images/'
verbose = True

upload_again = True
attempt_download = True
direct_upload = True
username, password = 'admin', '123'

#data = Table.read('../trial_sample/lensed_quasars_uploadtable.fits')]
lenses = Lenses.objects.all()

surveys = ['PanSTARRS', 'LegacySurveyDR10'] #, 'LegacySurveyNorth']
bandss = ['grizY', 'grz'] #, 'grz']
instruments = ['Pan-STARRS1', 'Legacy Survey (DR10)']#, 'Legacy Survey (North)']

for kk in range(len(surveys)):
    survey, bands, instrument = surveys[kk], bandss[kk], instruments[kk]
    uploads = []
    jsonfiles = list(set(glob.glob(jsonpath+'*_'+survey+'_*.json')) - set(glob.glob(jsonpath+'*_'+survey+'_*hotom*.json')))
    for i, jsonfile in enumerate(jsonfiles):

        #print(i)
        f = open(jsonfile)
        uploadjson = json.load(f)
        f.close()

        if uploadjson['exists']:
            uploadjson['image'] = imagepath + os.path.basename(uploadjson['image'])


        uploads.append(uploadjson)
        if i in np.arange(1000, len(jsonfiles)+5000, 1000):
            print(i, 'have been uploaded of', len(jsonfiles))
            upload = database_utils.upload_imaging_to_db_direct(datalist=uploads, username=username)
            uploads = []

    print(len(uploads))
    print('Uploading to database')
    upload = database_utils.upload_imaging_to_db_direct(datalist=uploads, username=username)
    #else:
    #    upload = database_utils.upload_data_to_db_API(datalist=uploads, datatype='Imaging', username=username, password=password)
