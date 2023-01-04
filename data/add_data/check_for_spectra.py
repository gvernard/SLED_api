from astropy.table import Table
import os
import json

import spectrum_utils
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


outpath = '../images_to_upload/'
jsonpath = outpath+'jsons/'
imagepath = outpath+'images/'
verbose = True
username, password = 'admin', '123'

survey = 'SDSS DR16'

uploads = []

#get all lenses, and see which have not been checked for spectra
lenses = Lenses.objects.all()
for lens in lenses:
    allspectra = Spectrum.objects.all().filter(lens=lens)
    if len(allspectra)==0:
        print('No spectra have been checked for', lens.name)

        name, ra, dec = lens.name, float(lens.ra), float(lens.dec)
        spectra = spectrum_utils.query_vizier_sdss_dr16(ra, dec, radius=5.)
        has_valid_spectrum = False
        if spectra is not None:
            if verbose:
                print('SDSS DR16 spectrum found for', name, ra, dec)
            for spec in spectra:
                jsonfile = jsonpath+name+'_SDSSDR16_'+spec['Sp-ID']+'.json'

                #check flag to see if spectrum was unplugged
                flag = spec['f_zsp']
                if "{:08d}".format(int(format(flag, 'b')))[-8]=='1':
                    if verbose:
                        print('There was a spectrum but the fiber was unplugged')
                    continue
                if verbose:
                    print('getting spectrum')

                has_valid_spectrum = True
                spid = spec['Sp-ID']
                title_string = spec['spCl']+'-'+spec['subCl']+'; z='+'{0:.3f}'.format(spec['zsp'])
                fits_outname = name+'_SDSSDR16_'+spid+'.fits'
                jpg_outname = name+'_SDSSDR16_'+spid+'.jpg'
                spectrum_utils.download_spectrum(spid, fits_outname=jsonpath+fits_outname)
                spectrum_utils.make_cutout(fits_outname=jsonpath+fits_outname, jpg_outname=imagepath+jpg_outname, title_string=title_string)
                upload_json = spectrum_utils.get_upload_json(ra='{0:.4f}'.format(ra), dec='{0:.4f}'.format(dec), jpg_outname=imagepath+jpg_outname, json_outname=jsonfile, fits_outname=jsonpath+fits_outname, spec_table=spec)
                
                uploads.append(upload_json)

        if not has_valid_spectrum:
            jsonfile = jsonpath+name+'_SDSSDR16.json'
            if verbose:
                print('No SDSS spectrum found for', name)
                print('Creating JSON to store as a negative result')        
            upload_json = spectrum_utils.checked_and_nodata_json(json_outname=jsonfile, ra=ra, dec=dec, instrument='SDSS-spec')
            uploads.append(upload_json)

upload = database_utils.upload_spectrum_to_db_direct(datalist=uploads, username=username)