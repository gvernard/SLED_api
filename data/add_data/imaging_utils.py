from astropy.time import Time
import json

def checked_and_nodata_json(json_outname, name, ra, dec, band, instrument):
    """
    To keep track of which data has a negative result (i.e. does not exist),
    we will store these as negative entries (exists=False) in the data tables
    This function creates the relevant jsons. Only for upload directly! Otherwise
    will have to change lots of code... check if no image exists, confirmation etc.
    """
    upload_json = {}
    upload_json['instrument'] = instrument
    upload_json['band'] = band
    upload_json['access_level'] = 'PUB'
    upload_json['ra'] = ra
    upload_json['dec'] = dec
    upload_json['exists'] = False
    upload_json['exposure_time'] = 1.
    upload_json['date_taken'] = Time(0., format='mjd').fits.replace('T', ' ')

    outfile = open(json_outname, 'w')
    json.dump(upload_json, outfile)
    outfile.close()

    return upload_json