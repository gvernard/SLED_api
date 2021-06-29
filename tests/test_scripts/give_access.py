import sys
import os
import django

base_dir = '../../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, SledGroups, Lenses
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from guardian.shortcuts import get_objects_for_user
from guardian.core import ObjectPermissionChecker


def accessible_objects_per_user():
    users = Users.objects.all()
    for user in users:
        lenses = Lenses.accessible_objects.all(user)
        print(user.username,len(lenses))


cameron = Users.objects.get(username='Cameron')
giorgos = Users.objects.get(username='Giorgos')
fred    = Users.objects.get(username='Fred')
groupA  = SledGroups.objects.get(name="Awesome Users")


accessible_objects_per_user()


# Owner gives access to private lenses
private_lenses = Lenses.accessible_objects.all(cameron).filter(access_level='private')
for i in range(0,3):    
    cameron.giveAccess(private_lenses[i],giorgos)

for i in range(6,10):
    cameron.giveAccess(private_lenses[i],groupA)
print()
accessible_objects_per_user()


cameron.revokeAccess(private_lenses[0],giorgos)
print()
accessible_objects_per_user()

public_lenses = Lenses.accessible_objects.all(cameron).filter(access_level='public')
cameron.revokeAccess(public_lenses[0],giorgos)
print()
accessible_objects_per_user()

    




'''
all_lenses = Lenses.objects.all()
for i, lens in enumerate(all_lenses):
    if i < 20:
        #assign_perm('has_access', user1, lens)
        assign_perm('view_lenses', user1, lens)
        print('Giving access to ', lens.name, 'to ', user1.username)
    if i > 89:
        #assign_perm('has_access', user2, lens)
        assign_perm('view_lenses', user2, lens)
        print('Giving access to ', lens.name, 'to ', user2.username)
        #print(user2.has_perm('has_access', lens))
    if 40 < i and i < 45:
        assign_perm('view_lenses', group1, lens)
        print('Giving access to ', lens.name, 'to ', group1.name)
'''        
