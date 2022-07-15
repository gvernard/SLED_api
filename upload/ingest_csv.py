import csv
import os


import sys
sys.path.append('../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django
django.setup()

from django.conf import settings
from lenses.models import Imaging, Spectrum, Instrument, Band, Users, Lenses

sys.path.append('../data/add_data/')
import panstarrs_utils
import legacysurvey_utils

import tasks



file = '../documentation/docs/upload/csvs/paper_lenses/canarias_2016MNRAS.461L..67B.csv'

#rename some of the header keywords to match our database schema
old_keywords = ['image_separation', 'redshift_lens', 'redshift_lens_secure', 'redshift_source', 'redshift_source_secure', 'uploader_comment', 'n_images']
new_keywords = ['image_sep', 'z_lens', 'z_lens_secure', 'z_source', 'z_source_secure', 'info', 'n_img']

with open(file, mode='r') as infile:
    rows = csv.DictReader(infile, skipinitialspace=True)
    headers = rows.fieldnames
    for old_kw, new_kw in zip(old_keywords, new_keywords):
        headers[headers.index(old_kw)] = new_kw

    a = [{k: v if v.strip() is not '' else None for k, v in row.items()}
        for row in rows]





user = Users.objects.get(username='Cameron')

#loop through the csv file and create lens instances for each new system
uploads = []
for system in a:

    lens = Lenses(ra=system['ra'], dec=system['dec'], owner=user)
    names = system['name'].split(',')
    lens.name = names[0].replace(' ', '')
    if len(names)>1:
        lens.alt_name = ','.join(names[1:])

    for field in ['ra', 'dec', 'flag_confirmed', 'flag_contaminant', 'image_sep', 'z_source', 'z_lens', 'n_img', 'info', 'candidate_score', 'lens_type', 'source_type', 'contaminant_type', 'candidate_score', 'image_configuration']:
        setattr(lens, field, system[field])

    #mugshotname = lens.name.replace(' ', '')+'.png'
    mugshotname = system['imagename']

    #panstarrs_colour_image.savecolorim(ra=lens.ra, dec=lens.dec, arcsec_width=10, outpath='./'+lens.name.strip()+'.png')
    legacysurvey_utils.savecolorim(ra=lens.ra, dec=lens.dec, arcsec_width=10, outpath='./'+mugshotname)

    current_image_location = './'
    os.system('mv '+current_image_location+mugshotname+' '+settings.MEDIA_ROOT+'/lenses/' + mugshotname)
    lens.mugshot.name = 'lenses/'+mugshotname

    uploads.append(lens)


Lenses.objects.bulk_create(uploads)

for lens in uploads:
    lens = Lenses.objects.get(name=lens.name)
    fname = 'upload_'+str(lens.id) + '.png'
    os.system('mv '+settings.MEDIA_ROOT+'/'+lens.mugshot.name+' '+settings.MEDIA_ROOT+'/lenses/' + fname)
    lens.mugshot.name = 'lenses/' + fname
    lens.save()

    tasks.get_imaging(name=lens.name, ra=float(lens.ra), dec=float(lens.dec), survey='PanSTARRS', bands='grizY', instrument='Pan-STARRS1')
    tasks.get_imaging(name=lens.name, ra=float(lens.ra), dec=float(lens.dec), survey='LegacySurveySouth', bands='grz', instrument='Legacy Survey (South)')
    tasks.get_imaging(name=lens.name, ra=float(lens.ra), dec=float(lens.dec), survey='LegacySurveyNorth', bands='grz', instrument='Legacy Survey (North)')



'''
admin = Users.objects.get(username='admin')
for j in range(0,len(users)-1):
    lensedquasars = Lenses.objects.filter(owner=users[j])
    assign_perm('view_lenses', users[j], lensedquasars)

    # Main activity stream for public lenses
    pub = list(Lenses.objects.filter(owner=users[j]).filter(access_level='PUB'))
    if len(pub) > 0:
        ad_col = AdminCollection.objects.create(item_type="Lenses",myitems=pub)
        action.send(users[j],target=Users.getAdmin().first(),verb='Add',level='success',action_object=ad_col)'''

