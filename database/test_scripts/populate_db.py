import sys
import os
import django

base_dir = '../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lensdb.models import Users, Groups, Lenses
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
#for name in names:
#    user = Users.objects.get(username=name)
#    print(model_to_dict(user))


groups = ['Awesome Users']
print('Populating the database with the following groups:', groups)
for name in groups:
    group = Groups(name=name)
    group.save()




# Adding users to group, need to have set the IDs
my_group = Groups.objects.get(name='Awesome Users') 
user1 = Users.objects.get(username='Cameron')
user2 = Users.objects.get(username='Fred')
user1.groups.add(my_group)
user2.groups.add(my_group)
#my_group.user_set.add(user1)
#my_group.user_set.add(user2)

user1 = Users.objects.get(username='Cameron')
print(model_to_dict(user1))
user2 = Users.objects.get(username='Fred')
print(model_to_dict(user2))


# Adding lenses
N = 100
print('Populating the database with '+str(N)+' random lenses')
ras = np.random.uniform(0, 360, N)
decs = np.random.uniform(-90, 90, N) #NOT UNIFORMLY DISTRIBUTED ON A SPHERE!
for i in range(N):
    ra, dec = ras[i], decs[i]
    c = SkyCoord(ra=ra*u.degree, dec=dec*u.degree, frame='icrs')
    Jname = 'J'+c.to_string('hmsdms')

    lens = Lenses(ra=ra, dec=dec, name=Jname, owner_id=user)
    lens.save()

#lenses = Lenses.objects.all()

