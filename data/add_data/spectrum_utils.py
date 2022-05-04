import panstarrs_utils
import astropy.io.fits as fits
from astropy.time import Time
                
import requests
from requests.auth import HTTPBasicAuth
import os

import matplotlib.pyplot as plt
import numpy as np
from astroquery.sdss import SDSS
from astropy import coordinates as coords
from scipy.ndimage import gaussian_filter

from astropy.table import Table
import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np 
from astroquery.vizier import Vizier
import json

def query_vizier_sdss_dr16(ra, dec, radius=5.):
    """
    ra, dec (float, float): coordinates in decimal, J2000
    radius: search radius in arcseconds for finding a spectrum

    Returns: None if no spectra are found within the radius
             A table with spectral entries
    """
    SDSS = Vizier(catalog="V/154/sdss16", columns=['zsp', 'spCl', 'subCl', 'Sp-ID', 'spInst', 'f_zsp'])
    SDSS.ROW_LIMIT = -1
    coord = SkyCoord(ra=ra, dec=dec, unit=(u.degree, u.degree), frame='icrs')
    spectra = SDSS.query_region(coord, radius=radius*u.arcsec, column_filters={'spInst': '!='})
    if len(spectra)==0:
        return None
    else:
        return spectra[0]


def download_spectrum(spid, fits_outname):
    """
    spid (str): plate-mjd-fibre string from SDSS 
    fits_outname (str): the filename including path for saving the spectrum fits file
    """
    plate = spid.split('-')[0]
    mjd = spid.split('-')[1]
    fibre = spid.split('-')[2]
    plate = "{:04d}".format(int(plate))
    url = 'https://dr16.sdss.org/sas/dr16/sdss/spectro/redux/26/spectra/lite/'+plate+'/spec-'+plate+'-'+mjd+'-'+fibre+'.fits'
    print(url)
    r = requests.get(url)
    if r.status_code != 200:
        url = 'https://dr16.sdss.org/sas/dr16/eboss/spectro/redux/v5_13_0/spectra/lite/'+plate+'/spec-'+plate+'-'+mjd+'-'+fibre+'.fits'
        r = requests.get(url)



    open(fits_outname,"wb").write(r.content)
    return fits_outname


def make_cutout(fits_outname, jpg_outname, title_string):
    data = fits.open(fits_outname)[1]

    error = 1./data.data['ivar']**0.5
    maxvals = data.data['flux']+error
    minvals = data.data['flux']-error
    wavs = 10.**data.data['loglam']

    fig = plt.figure(figsize=(11., 3.5))
    ax = fig.add_subplot(111)
    ax.plot(wavs, gaussian_filter(data.data['flux'], 0.2), color='black', lw=0.8)
    ax.plot(wavs, gaussian_filter(data.data['model'], 0.2), color='blue', lw=0.5)
    ax.fill_between(wavs, maxvals, minvals, alpha=0.4, edgecolor='k', facecolor='k', linewidth=0)
    ax.set_xlabel(r'wavelength (${\AA}$)', fontsize=17)
    ax.set_ylabel(r'$f_{\lambda} \ \ $ 10$^{-17}$ erg/s/cm$^{2}$/${\AA}$', fontsize=17)
    ax.set_xlim(np.nanmin(wavs), np.nanmax(wavs))
    ax.set_title(title_string)
    plt.savefig(jpg_outname, bbox_inches='tight', pad_inches=0.2, format='jpg')
    plt.close()
    return 0

def get_upload_json(ra, dec, jpg_outname, json_outname, fits_outname, spec_table):

    upload_json = {}
    datahdu = fits.open(fits_outname)[1].data
    header = data = fits.open(fits_outname)[0].header
    wavs = 10.**datahdu['loglam']
    date = Time(header['MJD'], format='mjd')
    formatted_date = date.fits.replace('T', ' ')

    #upload_json['instrument'] = spec_table['spInst']+'-spec'
    upload_json['instrument'] = 'SDSS-spec'
    upload_json['access_level'] = 'PUB'
    upload_json['ra'] = ra
    upload_json['dec'] = dec
    upload_json['date_taken'] = formatted_date
    upload_json['lambda_min'] = float('{0:.0f}'.format(np.nanmin(wavs)))
    upload_json['lambda_max'] = float('{0:.0f}'.format(np.nanmax(wavs)))
    upload_json['exposure_time'] = int(header['EXPTIME'])
    upload_json['resolution'] = int(np.median(wavs[1:]/(wavs[1:]-wavs[:-1])))
    upload_json['image'] = jpg_outname
    upload_json['future'] = False
    upload_json['info'] = None
    upload_json['exists'] = True

    outfile = open(json_outname, 'w')
    json.dump(upload_json, outfile)
    outfile.close()
    
    return upload_json


def checked_and_nodata_json(json_outname, ra, dec, instrument):
    """
    To keep track of which data has a negative result (i.e. does not exist),
    we will store these as negative entries (exists=False) in the data tables
    This function creates the relevant jsons. Only for upload directly! Otherwise
    will have to change lots of code... check if no image exists, confirmation etc.
    """
    upload_json = {}
    upload_json['instrument'] = instrument
    upload_json['access_level'] = 'PUB'
    upload_json['ra'] = ra
    upload_json['dec'] = dec
    upload_json['future'] = False
    upload_json['exists'] = False

    outfile = open(json_outname, 'w')
    json.dump(upload_json, outfile)
    outfile.close()

    return upload_json