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

user_array = [{'username':'Cameron',
               'first_name':'Cameron',
               'last_name':'Lemon',
               'email':'cameron.lemon@epfl.ch'
               },
              {'username':'gvernard',
               'first_name':'Giorgos',
               'last_name':'Vernardos',
               'email':'georgios.vernardos@epfl.ch'
               },
              {'username':'Fred',
               'first_name':'Fred',
               'last_name':'Courbin',
               'email':'fredcourbin@epfl.ch'
               },
              {'username':'herculens',
               'first_name':'Hercules',
               'last_name':'Demigod',
               'email':'hercu.god@epfl.ch'
               },
              {'username':'gizmo',
               'first_name':'Giz',
               'last_name':'Mo',
               'email':'giz.mo@epfl.ch'
               }
              ]
print('Populating the database with the following users:')
password = '123'

for user_details in user_array:
    user = Users.objects.create_user(username=user_details['username'], password=password,first_name=user_details['first_name'],last_name=user_details['last_name'],affiliation='EPFL', email=user_details['email'])
Users.objects.create_superuser(username='admin',password=password,email='admin@example.com')


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
user2 = Users.objects.get(username='gvernard')
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
#print(model_to_dict(user1))
user2 = Users.objects.get(username='Fred')
#print(model_to_dict(user2))



# Adding lenses
'''
N = 100
print('Populating the database with '+str(N)+' random lenses')
np.random.seed(666)
ras = np.random.uniform(0, 360, N)
decs = np.random.uniform(-90, 90, N) #NOT UNIFORMLY DISTRIBUTED ON A SPHERE!
mylenses = []
for i in range(N):
    ra, dec = ras[i], decs[i]

    lens = Lenses(ra=ra, dec=dec, owner=user1)
    lens.create_name()
    if i < 50:
        lens.access_level = SingleObject.AccessLevel.PUBLIC
    else:
        lens.access_level = SingleObject.AccessLevel.PRIVATE
        
    mylenses.append( lens )
    #lens.save() # first save, then assign permission
    #assign_perm('view_lenses',user1,lens)

Lenses.objects.bulk_create(mylenses)
mylenses = Lenses.objects.all()
pri = []
for lens in mylenses:
if lens.access_level == 'PRI':
pri.append(lens)
if pri:
assign_perm('view_lenses',user1,pri)

#lenses = Lenses.objects.all()

'''
