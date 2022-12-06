from astropy.table import Table
import os
import json
import glob

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

#name, ra, dec = 'SDSSJ0246-0825', 41.6420, -8.4267
outpath = '../images_to_upload/'
jsonpath = outpath+'jsons/'
imagepath = outpath+'images/'
verbose = True

upload_again = True
attempt_download = True
direct_upload = True
username, password = 'admin', '123'

survey = 'SDSS DR16'
offline = False

#data = Table.read('../trial_sample/lensed_quasars_uploadtable.fits')
lenses = Lenses.objects.all()

#for i in range(0, 50):
for kk, lens in enumerate(lenses): 
    uploads = []
    print(kk, len(lenses))
    name, ra, dec = lens.name, float(lens.ra), float(lens.dec)

    print('checking for spectra')
    if offline:
        spectra = glob.glob(jsonpath+name+'_SDSSDR16_*.json')
        if spectra is not None:
            specids = [spec.split('_')[-1][:-5] for spec in spectra]
    else:
        spectra = spectrum_utils.query_vizier_sdss_dr16(ra, dec, radius=5.)
        if spectra is not None:
            specids = spectra['Sp-ID']
    has_valid_spectrum = False
    if spectra is not None:
        if verbose:
            print('SDSS DR16 spectrum found for', name, ra, dec)
        for specnum, spec in enumerate(spectra):
            jsonfile = jsonpath+name+'_SDSSDR16_'+specids[specnum]+'.json'
            
            #if the json already exists, then no need to remake things
            if upload_again & os.path.exists(jsonfile):

                f = open(jsonfile)
                uploadjson = json.load(f)
                f.close()
                if uploadjson['exists']:
                    has_valid_spectrum = True

                if (not direct_upload) & uploadjson['exists']:
                    uploads.append(uploadjson)

                elif direct_upload:
                    uploads.append(uploadjson)

            if (not os.path.exists(jsonfile)) & attempt_download:
                #check flag to see if spectrum was unplugged
                flag = spec['f_zsp']
                if "{:08d}".format(int(format(flag, 'b')))[-8]=='1':
                    if verbose:
                        print('There was a spectrum but the fiber was unplugged')
                    continue

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
        if not os.path.exists(jsonfile):
            if verbose:
                print('No SDSS spectrum found for', name)
                print('Creating JSON to store as a negative result')        
            upload_json = spectrum_utils.checked_and_nodata_json(json_outname=jsonfile, ra=ra, dec=dec, instrument='SDSS-spec')
            if direct_upload:
                uploads.append(upload_json)
        if os.path.exists(jsonfile) & upload_again:
            f = open(jsonfile)
            upload_json = json.load(f)
            f.close()
            if direct_upload:
                uploads.append(upload_json)

    if len(uploads)>0:
        if direct_upload:
            upload = database_utils.upload_spectrum_to_db_direct(datalist=uploads, username=username)
        else:
            upload = database_utils.upload_data_to_db_API(uploads, 'Spectrum', username, password)
