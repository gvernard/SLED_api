import numpy as np
import astropy.io.fits as fits
import csv
from astropy.table import Table
import pandas as pd

csv_outname = 'silo_talbot_2021MNRAS.502.4617T.csv'
bibcode = '2021MNRAS.502.4617T'
datafile = '/Users/cameron/Downloads/silo_eboss_detections-1.0.1.fits'

#import catalogue table
data = fits.open(datafile)[1].data
print(data.columns)
for column in data.columns:
    print(column.name, data[0][column.name])

NAME_COLNAME = 'SDSS_TARGET_NAME'

RA_COLNAME = 'RA'
DEC_COLNAME = 'DEC'

Z_SOURCE = 'DETECTION_Z'
Z_LENS = 'Z_NOQSO'

LENS_TYPE = 'TARGET_GALAXY_TYPE'
SCORE_COLNAME = 'TOTAL_GRADE'
score_conversions = {'A+':3.0, 'A':2.75, 'A-':2.5, 'B+':2.25, 'B':2., 'B-':1.75, 'C+':1.5, 'C':1.25, 'C-':1.0}

#to concatenate particular comments to be the uploader comment
COMMENT_COLNAME = 'COMMENT'

#prepare a FITS file with the correct headers

''''final_df = pd.DataFrame({'name':[], 'ra':[], 'dec':[], 'imagename':[], 'paper_id':[], 'flag_discovery':[],
                         'redshift_source':[], 'redshift_source_secure':[], 'flag_source_redshift':[],
                         'redshift_lens':[], 'redshift_lens_secure':[], 'flag_lens_redshift':[],
                         'source_type':[], 'lens_type':[],
                         'n_images':[], 'image_configuration':[], 'image_separation':[],
                         'flag_confirmed':[], 'flag_candidate':[], 'candidate_score':[], 
                         'flag_contaminant':[], 'contaminant_type':[],
                         'uploader_comment':[], 'other_comment':[]})'''


df = pd.DataFrame(data)
final_df = pd.DataFrame({})

final_df['name'] = df[NAME_COLNAME]
final_df['ra'] = df[RA_COLNAME]
final_df['dec'] = df[DEC_COLNAME]
final_df['imagename'] = ''
final_df['paper_id'] = bibcode
final_df['flag_discovery'] = True

final_df['redshift_source'] = df[Z_SOURCE]
final_df['redshift_source_secure'] = True
final_df['flag_source_redshift'] = True

final_df['redshift_lens'] = df[Z_LENS]
final_df['redshift_lens_secure'] = True
final_df['flag_lens_redshift'] = True

final_df['n_images'] = ''
final_df['image_configuration'] = ''
final_df['image_separation'] = ''

final_df['lens_type'] = df[LENS_TYPE]
final_df['source_type'] = 'EMISSION LINE GALAXY'

final_df['flag_confirmed'] = False
final_df['flag_contaminant'] = False
final_df['contaminant_type'] = ''

final_df['flag_candidate'] = True
final_df['candidate_score'] = [score_conversions[score] for score in df[SCORE_COLNAME]]

final_df['uploader_comment'] = df[COMMENT_COLNAME]
final_df['other_comment'] = ''

final_df.to_csv(csv_outname, index=False)