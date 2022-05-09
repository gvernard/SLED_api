from __future__ import print_function
import numpy
from astropy.table import Table
import requests
from PIL import Image
from io import BytesIO, StringIO

import astropy.io.fits as fits
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier

import matplotlib.pyplot as plt
import numpy as np
import json
import requests

ps1filename = "https://ps1images.stsci.edu/cgi-bin/ps1filenames.py"
fitscut = "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi"


def return_photometry_json(json_outname, ra, dec, band, phot, instrument):
    upload_json = {}

    upload_json['instrument'] = instrument
    upload_json['band'] = band
    upload_json['access_level'] = 'PUB'
    upload_json['ra'] = ra
    upload_json['dec'] = dec
    upload_json['radet'] = float('{0:.7f}'.format(phot['RA_ICRS']))
    upload_json['decdet'] = float('{0:.7f}'.format(phot['DE_ICRS']))
    upload_json['exists'] = True
    if np.isnan(float(phot[band+'mag'])):
        upload_json['mag'] = None
    else:
        upload_json['mag'] = float('{0:.3f}'.format(phot[band+'mag']))

    if np.isnan(float(phot['e_'+band+'mag'])):
        upload_json['Dmag'] = None
    else:
        upload_json['Dmag'] = float('{0:.3f}'.format(phot['e_'+band+'mag']))
    upload_json['distance'] = float('{0:.3f}'.format(3600.*(((phot['RA_ICRS']-ra)*np.cos(dec*np.pi/180.))**2. + (phot['DE_ICRS']-dec)**2.)**0.5))

    outfile = open(json_outname, 'w')
    json.dump(upload_json, outfile)
    outfile.close()

    return upload_json

def return_empty_photometry_json(json_outname, ra, dec, band, instrument):
    upload_json = {}

    upload_json['instrument'] = instrument
    upload_json['band'] = band
    upload_json['radet'] = ra
    upload_json['decdet'] = dec   
    upload_json['ra'] = ra
    upload_json['dec'] = dec    
    upload_json['exists'] = False

    outfile = open(json_outname, 'w')
    json.dump(upload_json, outfile)
    outfile.close()

    return upload_json

def query_vizier_gaiadr1(ra, dec, radius=5.):
    """
    ra, dec (float, float): coordinates in decimal, J2000
    radius: search radius in arcseconds for finding catalogue data

    Returns: None if no spectra are found within the radius
             A table with spectral entries
    """
    GaiaDR1 = Vizier(catalog="I/337/gaia", columns=['RA_ICRS', 'DE_ICRS', '<Gmag>', 'e_<FG>', '<FG>'])
    GaiaDR1.ROW_LIMIT = -1
    coord = SkyCoord(ra=ra, dec=dec, unit=(u.degree, u.degree), frame='icrs')
    photometry = GaiaDR1.query_region(coord, radius=radius*u.arcsec) #, column_filters={'spInst': '!='})
    if len(photometry)==0:
        return None
    else:
        photometry = photometry[0]
        photometry['Gmag'] = photometry['__Gmag_']
        photometry['e_Gmag'] =-2.5*np.log10(photometry['__FG_']-photometry['e__FG_'])+2.5*np.log10(photometry['__FG_'])
        return photometry

def query_vizier_gaiadr2(ra, dec, radius=5.):
    """
    ra, dec (float, float): coordinates in decimal, J2000
    radius: search radius in arcseconds for finding catalogue data

    Returns: None if no spectra are found within the radius
             A table with spectral entries
    """
    GaiaDR2 = Vizier(catalog="I/345/gaia2", columns=['RA_ICRS', 'DE_ICRS', 'Gmag', 'e_Gmag', 'BPmag', 'e_BPmag', 'RPmag', 'e_RPmag'])
    GaiaDR2.ROW_LIMIT = -1
    coord = SkyCoord(ra=ra, dec=dec, unit=(u.degree, u.degree), frame='icrs')
    photometry = GaiaDR2.query_region(coord, radius=radius*u.arcsec) #, column_filters={'spInst': '!='})
    if len(photometry)==0:
        return None
    else:
        photometry = photometry[0] 
        cleaned = np.array([not mask for mask in photometry['RA_ICRS'].mask])
        if cleaned.sum()==0:
            return None
        else:
            return photometry[cleaned]
