import astropy.io.fits as fits
from astropy.time import Time
                
import requests
from PIL import Image
from io import BytesIO, StringIO

from requests.auth import HTTPBasicAuth
import os
import json

import matplotlib.pyplot as plt
import numpy as np


def legacysurvey_data(name, ra, dec, band, layer='ls-dr9-south', outpath='./images_to_upload/', size=10, verbose=False):
    """
    name (string): for constructing the filenames
    ra, dec (float, float): coordinates to check for Pan-STARRS data
    band (string): which single band to download, choose from 'g', 'r', 'z'
    outpath (string): directory in which to store the files
    size (float): size cutout in arcseconds
    verbose (bool): will say if the data does not exist
    """
    if (layer=='ls-dr9-south') & ((dec > 36.3) or (dec < -68.7)):
        if verbose:
            print('No', layer, 'data exist for RA, Dec=', ra, dec, 'and filter', band)
        return None
    elif (layer=='ls-dr9-north') & ((dec > 84.8) or (dec < -3.2)):
        if verbose:
            print('No', layer, 'data exist for RA, Dec=', ra, dec, 'and filter', band)
        return None
    else:
        if layer=='ls-dr9-south':
            fits_outname = outpath+name+'_LegacySurveySouth_'+band+'.fits'
        if layer=='ls-dr9-north':
            fits_outname = outpath+name+'_LegacySurveyNorth_'+band+'.fits'
        outname = save_single_band_layer(fits_outname, ra, dec, size=size, band=band.lower(), layer=layer)
        if outname is None:
            if verbose:
                print('No ', layer,' data existed for RA, Dec=', ra, dec, 'and filter', band)
            return None
        return fits_outname


def save_single_band_layer(fits_outname, ra, dec, size=10, band='g', layer='ls-dr9-south'):
    url = 'https://www.legacysurvey.org/viewer/fits-cutout?ra='+str(ra)+'&dec='+str(dec)+'&layer='+layer+'&pixscale=0.262&size='+str(int(size/0.262)+1)+'&bands='+band
    r = requests.get(url)
    #if r.status_code==500:
    #    return None
    if r.status_code!=200:
        return None
    open(fits_outname,"wb").write(r.content)
    data = fits.open(fits_outname)[0].data
    if np.nanmax(data)==0.:
        return None
    return fits_outname

def legacy_survey_layer_band_image_and_json(name, ra, dec, band, layer, jsonpath, imagepath, size=10):
    """
    parameter explanations
    """
    if layer=='ls-dr9-south':
        instrument, pixel_size, filemiddle = 'Legacy Survey (South)', 0.262, 'LegacySurveySouth'
    if layer=='ls-dr9-north':
        instrument, pixel_size, filemiddle = 'Legacy Survey (North)', 0.262, 'LegacySurveyNorth'
    access_level = 'PUB'

    upload_json = {}
    upload_json['instrument'] = instrument
    upload_json['pixel_size'] = pixel_size
    upload_json['band'] = band
    upload_json['access_level'] = 'PUB'
    upload_json['ra'] = ra
    upload_json['dec'] = dec
    upload_json['exists'] = True

    jpg_outname = imagepath+name+'_'+filemiddle+'_'+band+'.jpg'
    fits_outname = jsonpath+name+'_'+filemiddle+'_'+band+'.fits'
    json_outname = jsonpath+name+'_'+filemiddle+'_'+band+'.json'

    data = fits.open(fits_outname)[0].data
    
    plt.figure(figsize=(1.5, 1.5))
    plt.imshow(data, interpolation='nearest', origin='lower', cmap='cubehelix', vmax=np.nanpercentile(data, 99.), vmin=np.nanpercentile(data, 5.))
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(jpg_outname, bbox_inches='tight', pad_inches=0.01, format='jpg')
    plt.close()

    exptime = 1. #PLEASE COME BACK AND WORK OUT A WAY TO GET THIS INFO
    date = Time(0., format='mjd')
    formatted_date = date.fits.replace('T', ' ')
    upload_json['exposure_time'] = exptime
    upload_json['date_taken'] = formatted_date
    upload_json['image'] = jpg_outname
    upload_json['future'] = False
    upload_json['info'] = 'stack'

    outfile = open(json_outname, 'w')
    json.dump(upload_json, outfile)
    outfile.close()

    return json_outname

def legacy_survey_colour_image(ra, dec, layer='ls-dr9', size=60):
    """
    parameter explanations
    """
    url = 'https://www.legacysurvey.org/viewer/cutout.jpg?ra='+str(ra)+'&dec='+str(dec)+'&layer='+layer+'&pixscale=0.262'+'&size='+str(size)

    r = requests.get(url)
    im = Image.open(BytesIO(r.content))
    return im



def savecolorim(ra, dec, arcsec_width, outpath):
    size = int(arcsec_width/0.262)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    im = legacy_survey_colour_image(ra=ra, dec=dec, size=size)
    ax.imshow(im, origin='lower', interpolation='nearest')
    ax.set_xticks([])
    ax.set_yticks([])
    plt.savefig(outpath, bbox_inches='tight')
    plt.close()


