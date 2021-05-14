import sys
import os
import django

base_dir = '../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lensdb.models import Users, Lenses
from django.forms.models import model_to_dict

from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np

names = ['Cameron', 'Giorgos', 'Fred']
print('Populating the database with the following users:', names)

for name in names:
    user = Users(username=name)
    user.save()

#let's take a look at the fields and their values for this user
#user = Users.objects.get(username='Cameron')
#print(model_to_dict(user))

N = 100
print('Populating the database with '+str(N)+' random lenses')
ras = np.random.uniform(0, 360, N)
decs = np.random.uniform(-90, 90, N) #NOT UNIFORMLY DISTRIBUTED!
for i in range(N):
    ra, dec = ras[i], decs[i]
    c = SkyCoord(ra=ra*u.degree, dec=dec*u.degree, frame='icrs')
    Jname = 'J'+c.to_string('hmsdms')

    lens = Lenses(ra=ra, dec=dec, name=Jname, owner_id=user)
    lens.save()

#lenses = Lenses.objects.all()

