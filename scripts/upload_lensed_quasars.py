import sys
import os
import django
from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np
from astropy.table import Table

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, SledGroups, Lenses, SingleObject
from django.forms.models import model_to_dict
from guardian.shortcuts import assign_perm

user1 = Users.objects.get(username='Cameron')

# Adding lenses
print('Populating the database with known lensed quasars')
data = Table.read('./scripts/lensed_quasars_uploadtable.fits')
ras, decs = data['RA'], data['DEC']
names = data['Name']
z_source, z_lens = data['z_qso'], data['z_lens']
nimg = data['N_images']
separation = data['separation']
confirmed = data['confirmed']
access = data['access']

lensedquasars = []
for i in range(len(ras)):
    lens = Lenses(ra=ras[i], dec=decs[i], owner=user1)
    lens.name = names[i]
    #lens.create_name()
    lens.n_img = nimg[i]
    lens.flag_confirmed = confirmed[i]
    lens.image_sep = separation[i]
    try:
        z_s = float(z_source[i])
        lens.z_source = z_s
    except Exception:
        pass
    try:
        z_l = float(z_lens[i])
        lens.z_lens = z_l
    except Exception:
        pass
    if access[i]=='PRI':
        lens.access_level = SingleObject.AccessLevel.PRIVATE
    elif access[i]=='PUB':
        lens.access_level = SingleObject.AccessLevel.PUBLIC
        
    lensedquasars.append( lens )


Lenses.objects.bulk_create(lensedquasars)
#lensedquasars = Lenses.objects.all()
#assign_perm('view_lenses',user1,mylenses)

#lenses = Lenses.objects.all()

