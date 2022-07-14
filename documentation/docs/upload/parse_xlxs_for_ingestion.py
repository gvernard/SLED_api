import numpy as np
import astropy.io.fits as fits
import csv
from astropy.table import Table
import pandas as pd

csv_outname = 'huang21_desi_2021ApJ...909...27H.csv'
bibcode = '2021ApJ...909...27H'

#downloaded and stacked the three sheets from https://sites.google.com/usfca.edu/neuralens/publications/lens-candidates-huang-2020b?authuser=0
datafile = '/Users/cameron/database/SLED/huang21.xlsx'
sheetname = 'All'

#import catalogue table
data = pd.read_excel(datafile, sheet_name=sheetname)

print(data.columns)
for column in data.columns:
    print(column, data.iloc[0][column])

NAME_COLNAME = 'Name\n[2]'

RA_COLNAME = 'RA'
DEC_COLNAME = 'Dec'

#Z_SOURCE = 'DETECTION_Z'
#Z_LENS = 'Z_NOQSO'

#LENS_TYPE = 'TARGET_GALAXY_TYPE'
SCORE_COLNAME = 'Grade'
score_conversions = {'A':3.0, 'B':2.25, 'C':1.5}

#to concatenate particular comments to be the uploader comment
#COMMENT_COLNAME = 'COMMENT'

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

final_df['redshift_source'] = ''
final_df['redshift_source_secure'] = ''
final_df['flag_source_redshift'] = ''

final_df['redshift_lens'] = ''
final_df['redshift_lens_secure'] = ''
final_df['flag_lens_redshift'] = ''

final_df['n_images'] = ''
final_df['image_configuration'] = ''
final_df['image_separation'] = ''

final_df['lens_type'] = ''
final_df['source_type'] = ''

final_df['flag_confirmed'] = False
final_df['flag_contaminant'] = False
final_df['contaminant_type'] = ''

final_df['flag_candidate'] = True
final_df['candidate_score'] = [score_conversions[score] for score in df[SCORE_COLNAME]]
final_df['original_score'] = df[SCORE_COLNAME]

final_df['uploader_comment'] = ''
final_df['other_comment'] = ''

final_df.to_csv(csv_outname, index=False)