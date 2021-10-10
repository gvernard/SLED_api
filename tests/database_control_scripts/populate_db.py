import sys
import os
import django
from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, SledGroups, Lenses, SingleObject
from django.forms.models import model_to_dict
from guardian.shortcuts import assign_perm

names = ['Cameron', 'Giorgos', 'Fred']
print('Populating the database with the following users:', names)
password = '123'

for name in names:
    print(name)
    user = Users.objects.create_user(username=name, password=password, affiliation='EPFL', email=name+'@epfl.ch')




#let's take a look at the fields and their values for this user
#for name in names:
#    user = Users.objects.get(username=name)
#    print(model_to_dict(user))


groups = ['Awesome Users', 'TDCOSMO']
descriptions = ['A group for awesome users', 'Time delay cosmography with lensed quasars']
print('Populating the database with the following groups:', groups)
for i, name in enumerate(groups):
    group = SledGroups(name=name, description=descriptions[i])
    group.save()



# Adding users to group, need to have set the IDs
my_group = SledGroups.objects.get(name='Awesome Users') 
user1 = Users.objects.get(username='Cameron')
user2 = Users.objects.get(username='Giorgos')
user3 = Users.objects.get(username='Fred')
user2.groups.add(my_group)
user3.groups.add(my_group)

my_group = SledGroups.objects.get(name='TDCOSMO') 
user1.groups.add(my_group)
user2.groups.add(my_group)
user3.groups.add(my_group)

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
mylenses = []
for i in range(N):
    ra, dec = ras[i], decs[i]
    c = SkyCoord(ra=ra*u.degree, dec=dec*u.degree, frame='icrs')
    Jname = 'J'+c.to_string('hmsdms')
    #Jname = 'J'+str(ra)+str(dec)
    
    if i < 50:
        access_level = SingleObject.AccessLevel.PUBLIC
    else:
        access_level = SingleObject.AccessLevel.PRIVATE
    
    mylenses.append( Lenses(ra=ra, dec=dec, name=Jname, access_level=access_level, owner=user1) )
    #lens.save() # first save, then assign permission
    #assign_perm('view_lenses',user1,lens)

Lenses.objects.bulk_create(mylenses)
mylenses = Lenses.objects.all()
assign_perm('view_lenses',user1,mylenses)

#lenses = Lenses.objects.all()

