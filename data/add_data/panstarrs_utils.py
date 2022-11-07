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


def return_photometry_json(json_outname, ra, dec, band, phot):
    upload_json = {}

    upload_json['instrument'] = 'Pan-STARRS1'
    upload_json['band'] = band
    upload_json['access_level'] = 'PUB'
    upload_json['ra'] = ra
    upload_json['dec'] = dec
    upload_json['radet'] = float('{0:.7f}'.format(phot['RAJ2000']))
    upload_json['decdet'] = float('{0:.7f}'.format(phot['DEJ2000']))
    upload_json['exists'] = True
    if np.isnan(float(phot[band.lower()+'mag'])):
        upload_json['mag'] = None
    else:
        upload_json['mag'] = float('{0:.3f}'.format(phot[band.lower()+'mag']))

    if np.isnan(float(phot['e_'+band.lower()+'mag'])):
        upload_json['Dmag'] = None
    else:
        upload_json['Dmag'] = float('{0:.3f}'.format(phot['e_'+band.lower()+'mag']))
    upload_json['distance'] = float('{0:.3f}'.format(3600.*(((phot['RAJ2000']-ra)*np.cos(dec*np.pi/180.))**2. + (phot['DEJ2000']-dec)**2.)**0.5))

    outfile = open(json_outname, 'w')
    json.dump(upload_json, outfile)
    outfile.close()

    return upload_json

def return_empty_photometry_json(json_outname, ra, dec, band):
    upload_json = {}

    upload_json['instrument'] = 'Pan-STARRS1'
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

def query_vizier_panstarrs(ra, dec, radius=5.):
    """
    ra, dec (float, float): coordinates in decimal, J2000
    radius: search radius in arcseconds for finding catalogue data

    Returns: None if no spectra are found within the radius
             A table with spectral entries
    """
    PanSTARRS = Vizier(catalog="II/349/ps1", columns=['RAJ2000', 'DEJ2000', 'gmag', 'e_gmag', 'rmag', 'e_rmag', 'imag', 'e_imag', 'zmag', 'e_zmag', 'ymag', 'e_ymag'])
    PanSTARRS.ROW_LIMIT = -1
    coord = SkyCoord(ra=ra, dec=dec, unit=(u.degree, u.degree), frame='icrs')
    photometry = PanSTARRS.query_region(coord, radius=radius*u.arcsec) #, column_filters={'spInst': '!='})
    if len(photometry)==0:
        return None
    else:
        return photometry[0]



def getimages(ra,dec,size=240,filters="grizy"):
    
    """Query ps1filenames.py service to get a list of images
    
    ra, dec = position in degrees
    size = image size in pixels (0.25 arcsec/pixel)
    filters = string with filters to include
    Returns a table with the results
    """
    
    service = "https://ps1images.stsci.edu/cgi-bin/ps1filenames.py"
    url = ("{service}?ra={ra}&dec={dec}&size={size}&format=fits"
           "&filters={filters}").format(**locals())
    table = Table.read(url, format='ascii')
    return table

def geturl(ra, dec, size=240, output_size=None, filters="grizy", format="jpg", color=False):
    
    """Get URL for images in the table
    
    ra, dec = position in degrees
    size = extracted image size in pixels (0.25 arcsec/pixel)
    output_size = output (display) image size in pixels (default = size).
                  output_size has no effect for fits format images.
    filters = string with filters to include
    format = data format (options are "jpg", "png" or "fits")
    color = if True, creates a color image (only for jpg or png format).
            Default is return a list of URLs for single-filter grayscale images.
    Returns a string with the URL
    """
    
    if color and format == "fits":
        raise ValueError("color images are available only for jpg or png formats")
    if format not in ("jpg","png","fits"):
        raise ValueError("format must be one of jpg, png, fits")
    table = getimages(ra,dec,size=size,filters=filters)
    url = ("https://ps1images.stsci.edu/cgi-bin/fitscut.cgi?"
           "ra={ra}&dec={dec}&size={size}&format={format}").format(**locals())
    if output_size:
        url = url + "&output_size={}".format(output_size)
    # sort filters from red to blue
    flist = ["yzirg".find(x) for x in table['filter']]
    table = table[numpy.argsort(flist)]
    if color:
        if len(table) > 3:
            # pick 3 filters
            table = table[[0,len(table)//2,len(table)-1]]
        for i, param in enumerate(["red","green","blue"]):
            url = url + "&{}={}".format(param,table['filename'][i])
    else:
        urlbase = url + "&red="
        url = []
        for filename in table['filename']:
            url.append(urlbase+filename)
    return url

def getimages2(tra, tdec, size=240, filters="grizy", format="fits", imagetypes="stack"):
     
    """Query ps1filenames.py service for multiple positions to get a list of images
    This adds a url column to the table to retrieve the cutout.
     
    tra, tdec = list of positions in degrees
    size = image size in pixels (0.25 arcsec/pixel)
    filters = string with filters to include
    format = data format (options are "fits", "jpg", or "png")
    imagetypes = list of any of the acceptable image types.  Default is stack;
        other common choices include warp (single-epoch images), stack.wt (weight image),
        stack.mask, stack.exp (exposure time), stack.num (number of exposures),
        warp.wt, and warp.mask.  This parameter can be a list of strings or a
        comma-separated string.
 
    Returns an astropy table with the results
    """
     
    if format not in ("jpg","png","fits"):
        raise ValueError("format must be one of jpg, png, fits")
    # if imagetypes is a list, convert to a comma-separated string
    if not isinstance(imagetypes,str):
        imagetypes = ",".join(imagetypes)
    # put the positions in an in-memory file object
    cbuf = StringIO()
    cbuf.write('\n'.join(["{} {}".format(ra, dec) for (ra, dec) in zip(tra,tdec)]))
    cbuf.seek(0)
    # use requests.post to pass in positions as a file
    r = requests.post(ps1filename, data=dict(filters=filters, type=imagetypes),
        files=dict(file=cbuf))
    r.raise_for_status()
    if '\n' not in r.text:
        return None
    tab = Table.read(r.text, format="ascii")
 
    urlbase = "{}?size={}&format={}".format(fitscut,size,format)
    tab["url"] = ["{}&ra={}&dec={}&red={}".format(urlbase,ra,dec,filename)
            for (filename,ra,dec) in zip(tab["filename"],tab["ra"],tab["dec"])]
    return tab

def save_single_band_stack_fits(outname, ra, dec, size=240, filter="g"):
    """
    ra, dec = position
    size in ARCSECONDS
    """
    tab = getimages2(tra=[ra], tdec=[dec], size=int(size/0.25), filters=filter, format="fits", imagetypes="stack")
    if tab is None:
        return None
    url = tab['url'][0]
    r = requests.get(url)
    open(outname,"wb").write(r.content)
    return outname


def getcolorim(ra, dec, size=240, output_size=None, filters="grizy", format="png"):
    
    """Get color image at a sky position
    
    ra, dec = position in degrees
    size = extracted image size in pixels (0.25 arcsec/pixel)
    output_size = output (display) image size in pixels (default = size).
                  output_size has no effect for fits format images.
    filters = string with filters to include
    format = data format (options are "jpg", "png")
    Returns the image
    """
    
    if format not in ("jpg","png"):
        raise ValueError("format must be jpg or png")
    url = geturl(ra,dec,size=size,filters=filters,output_size=output_size,format=format,color=True)
    print(url)
    r = requests.get(url)
    print(r)
    im = Image.open(BytesIO(r.content))
    return im


def getgrayim(ra, dec, size=240, output_size=None, filter="g", format="jpg"):
    
    """Get grayscale image at a sky position
    
    ra, dec = position in degrees
    size = extracted image size in pixels (0.25 arcsec/pixel)
    output_size = output (display) image size in pixels (default = size).
                  output_size has no effect for fits format images.
    filter = string with filter to extract (one of grizy)
    format = data format (options are "jpg", "png")
    Returns the image
    """
    
    if format not in ("jpg","png"):
        raise ValueError("format must be jpg or png")
    if filter not in list("grizy"):
        raise ValueError("filter must be one of grizy")
    print('getting filter', filter)
    url = geturl(ra,dec,size=size,filters=filter,output_size=output_size,format=format)
    r = requests.get(url[0])
    im = Image.open(BytesIO(r.content))
    return im

def download_and_save(ra, dec, size, outname, output_size=None, filters="grizy", format="jpg"):
    """Download and color image at a sky position
    
    ra, dec = position in degrees
    size = extracted image size in ARCSECONDS (CONVERTED WITH pixels (0.25 arcsec/pixel))
    outname = savename for file
    output_size = output (display) image size in pixels (default = size).
                  output_size has no effect for fits format images.
    filters = string with filters to include
    format = data format (options are "jpg", "png")
    Returns the image
    """
    if len(filters)>1:
        im = getcolorim(ra=ra, dec=dec, size=int(size/0.25), output_size=output_size, filters=filters, format=format)
    else:
        im = getgrayim(ra=ra, dec=dec, size=int(size/0.25), output_size=output_size, filter=filters, format=format)
    im.save(outname)
    return outname

def panstarrs_data(name, ra, dec, band, outpath='./images_to_upload/', size=10, verbose=False):
    """
    name (string): for constructing the filenames
    ra, dec (float, float): coordinates to check for Pan-STARRS data
    band (string): which single band to download, choose from 'g', 'r', 'i', 'z', and 'Y'
    outpath (string): directory in which to store the files
    size (float): size cutout in arcseconds
    verbose (bool): will say if the data does not exist
    """
    if dec < -32.:
        if verbose:
            print('No stacked PanSTARRS data existed for RA, Dec=', ra, dec, 'and filter', band)
        return None
    else:
        fits_outname = outpath+name+'_PanSTARRS_'+band+'.fits'
        outname = save_single_band_stack_fits(fits_outname, ra, dec, size=size, filter=band.lower())
        if outname is None:
            if verbose:
                print('No stacked PanSTARRS data existed for RA, Dec=', ra, dec, 'and filter', band)
            return None
        return fits_outname


def panstarrs_band_image_and_json(name, ra, dec, band, jsonpath, imagepath, size=10):
    """
    parameter explanations
    """
    instrument, pixel_size = 'Pan-STARRS1', 0.25

    upload_json = {}
    upload_json['instrument'] = instrument
    upload_json['pixel_size'] = pixel_size
    upload_json['band'] = band
    upload_json['access_level'] = 'PUB'
    upload_json['ra'] = ra
    upload_json['dec'] = dec
    upload_json['exists'] = True

    jpg_outname = imagepath+name+'_PanSTARRS_'+band+'.jpg'
    fits_outname = jsonpath+name+'_PanSTARRS_'+band+'.fits'
    json_outname = jsonpath+name+'_PanSTARRS_'+band+'.json'
    #panstarrs_utils.download_and_save(ra, dec, size, jpg_outname, output_size=None, filters=band.lower(), format="jpg")

    #make our own single band colour image
    header = fits.open(fits_outname)[0].header
    data = fits.open(fits_outname)[0].data
    plt.figure(figsize=(1.5, 1.5))
    plt.imshow(data, interpolation='nearest', origin='lower', cmap='cubehelix', vmax=np.nanpercentile(data, 99.), vmin=np.nanpercentile(data, 5.))
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(jpg_outname, bbox_inches='tight', pad_inches=0.01, format='jpg')
    plt.close()

    #get the metadata for the json, including the path to the image
    exptime = header['EXPTIME']
    date = Time(header['MJD-OBS'], format='mjd')
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


def ps1cone(ra,dec,radius,table="mean",release="dr1",format="csv",columns=None,
           baseurl="https://catalogs.mast.stsci.edu/api/v0.1/panstarrs", verbose=False,
           **kw):
    """Do a cone search of the PS1 catalog
    
    Parameters
    ----------
    ra (float): (degrees) J2000 Right Ascension
    dec (float): (degrees) J2000 Declination
    radius (float): (degrees) Search radius (<= 0.5 degrees)
    table (string): mean, stack, or detection
    release (string): dr1 or dr2
    format: csv, votable, json
    columns: list of column names to include (None means use defaults)
    baseurl: base URL for the request
    verbose: print info about request
    **kw: other parameters (e.g., 'nDetections.min':2)
    """
    
    data = kw.copy()
    data['ra'] = ra
    data['dec'] = dec
    data['radius'] = radius
    return ps1search(table=table,release=release,format=format,columns=columns,
                    baseurl=baseurl, verbose=verbose, **data)


def ps1search(table="mean",release="dr1",format="csv",columns=None,
           baseurl="https://catalogs.mast.stsci.edu/api/v0.1/panstarrs", verbose=False,
           **kw):
    """Do a general search of the PS1 catalog (possibly without ra/dec/radius)
    
    Parameters
    ----------
    table (string): mean, stack, or detection
    release (string): dr1 or dr2
    format: csv, votable, json
    columns: list of column names to include (None means use defaults)
    baseurl: base URL for the request
    verbose: print info about request
    **kw: other parameters (e.g., 'nDetections.min':2).  Note this is required!
    """
    
    data = kw.copy()
    if not data:
        raise ValueError("You must specify some parameters for search")
    checklegal(table,release)
    if format not in ("csv","votable","json"):
        raise ValueError("Bad value for format")
    url = "{baseurl}/{release}/{table}.{format}".format(**locals())
    if columns:
        # check that column values are legal
        # create a dictionary to speed this up
        dcols = {}
        for col in ps1metadata(table,release)['name']:
            dcols[col.lower()] = 1
        badcols = []
        for col in columns:
            if col.lower().strip() not in dcols:
                badcols.append(col)
        if badcols:
            raise ValueError('Some columns not found in table: {}'.format(', '.join(badcols)))
        # two different ways to specify a list of column values in the API
        # data['columns'] = columns
        data['columns'] = '[{}]'.format(','.join(columns))

# either get or post works
#    r = requests.post(url, data=data)
    r = requests.get(url, params=data)

    if verbose:
        print(r.url)
    r.raise_for_status()
    if format == "json":
        return r.json()
    else:
        return r.text

def checklegal(table,release):
    """Checks if this combination of table and release is acceptable
    
    Raises a VelueError exception if there is problem
    """
    
    releaselist = ("dr1", "dr2")
    if release not in ("dr1","dr2"):
        raise ValueError("Bad value for release (must be one of {})".format(', '.join(releaselist)))
    if release=="dr1":
        tablelist = ("mean", "stack")
    else:
        tablelist = ("mean", "stack", "detection")
    if table not in tablelist:
        raise ValueError("Bad value for table (for {} must be one of {})".format(release, ", ".join(tablelist)))


def savecolorim(ra, dec, arcsec_width, outpath):
    size = int(arcsec_width/0.25)
    #plt.figure()
    im = getcolorim(ra=ra, dec=dec, size=size)
    fig, ax = plt.subplots()
    ax.imshow(im, interpolation='nearest')
    ax.set_xticks([])
    ax.set_yticks([])

    plt.savefig(outpath, bbox_inches='tight')

    plt.close()
