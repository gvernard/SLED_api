import os
import json
import glob
from astropy.table import Table

import panstarrs_utils
import legacysurvey_utils
import imaging_utils
import database_utils
import gaia_utils 

import sys
sys.path.append('../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django
django.setup()

from django.conf import settings
from lenses.models import Catalogue, Instrument, Band, Users, Lenses
from api.serializers import ImagingDataUploadSerializer
from django.db.models import Q, F, Func, FloatField, CheckConstraint

outpath='../images_to_upload/jsons/'
verbose = True

username, password = 'admin', '123'

#data = Table.read('../trial_sample/lensed_quasars_uploadtable.fits')]
lenses = Lenses.objects.all()

surveys = ['PanSTARRS', 'Gaia-DR1', 'Gaia-DR2']
bandss = ['grizY', 'G', ['G', 'BP', 'RP']]
instruments = ['Pan-STARRS1', 'Gaia-DR1', 'Gaia-DR2']

for kk in range(len(surveys)):
    survey, bands, instrument = surveys[kk], bandss[kk], instruments[kk]

    uploads = []
    lenses = Lenses.objects.all()
    for lens in lenses:
        for band in bands:
            #see whether spectra exist for this lens
            allcatalogues = Catalogue.objects.all().filter(lens=lens).filter(instrument__name=instrument).filter(band__name=band)
            if len(allcatalogues)==0:
                name, ra, dec = lens.name, float(lens.ra), float(lens.dec)
                print('No images have been checked for', name)
                if verbose:
                    print('checking for ', survey,' data in', band)
                jsonfile = outpath+name+'_'+survey+'_'+band+'_photometry1.json'
                #download the PanSTARRS data
                if survey=='PanSTARRS':
                    datafile = panstarrs_utils.query_vizier_panstarrs(ra, dec, radius=5.)
                if survey=='Gaia-DR1':
                    datafile = gaia_utils.query_vizier_gaiadr1(ra, dec, radius=5.)
                    print(survey, datafile)
                if survey=='Gaia-DR2':
                    datafile = gaia_utils.query_vizier_gaiadr2(ra, dec, radius=5.)
                    print(survey, datafile)

                #if the data exists, create the json and image for upload
                if datafile is not None:
                    for k, phot in enumerate(datafile):
                        print(name, ra, dec, k)
                        jsonname = outpath+name+'_'+survey+'_'+band+'_photometry'+str(k+1)+'.json'
                        if survey=='PanSTARRS':
                            uploadjson = panstarrs_utils.return_photometry_json(json_outname=jsonname, ra=ra, dec=dec, band=band, phot=phot)
                        if survey in ['Gaia-DR1', 'Gaia-DR2']:
                            print(survey)
                            uploadjson = gaia_utils.return_photometry_json(json_outname=jsonname, ra=ra, dec=dec, band=band, phot=phot, instrument=instrument)

                        uploads.append(uploadjson)

                #if the data does not exist, then upload an exists=False json so we know not to try again (DIRECT ONLY)
                if datafile is None:
                    if survey=='PanSTARRS':
                        uploadjson = panstarrs_utils.return_empty_photometry_json(json_outname=jsonfile, ra=ra, dec=dec, band=band)
                    if survey=='Gaia-DR1':
                        uploadjson = gaia_utils.return_empty_photometry_json(json_outname=jsonfile, ra=ra, dec=dec, band=band, instrument='Gaia-DR1')
                    if survey=='Gaia-DR2':
                        uploadjson = gaia_utils.return_empty_photometry_json(json_outname=jsonfile, ra=ra, dec=dec, band=band, instrument='Gaia-DR2')
                    uploads.append(uploadjson)

    if len(uploads)>0:
        upload = database_utils.upload_catalogue_to_db_direct(datalist=uploads, username=username)
