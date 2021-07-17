import sys
import os
import django
from random import randrange

base_dir = '../../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, SledGroups, Lenses
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import get_users_with_perms

from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np

'''
usernames = ['Cameron', 'Giorgos', 'Fred']
for username in usernames:
    user = Users.objects.get(username=username)
    #q = Lenses.objects.filter(ra__gte=180)
    #accessible_lenses = get_objects_for_user(user, 'has_access', klass=q)
    accessible_lenses = get_objects_for_user(user, 'lensdb.view_lenses',)
    print(username+' has access to '+str(len(accessible_lenses))+' lenses')


lenses = Lenses.objects.all()

N = len(lenses)
#index = randrange(N)
index = 43
lens = lenses[index]
print('The following have access to this lens:', index, get_users_with_perms(lens))
'''

users = Users.objects.all()

def accessible_objects_per_user():
    users = Users.objects.all()
    for user in users:
        lenses = Lenses.accessible_objects.all(user)
        print(user.username,len(lenses))



print("Owned objects per user: ")
for user in users:
    owned_objects = user.getOwnedObjects(["Lenses","dummy"])
    for key in owned_objects:
        print(user.username,key,len(owned_objects[key]))
print()

print("Groups that user belongs to: ")
for user in users:
    groups = user.getGroupsIsMember()
    print(user.username,groups.values_list('name',flat=True))
print()




print("Accessible objects per user: ")
accessible_objects_per_user()
print()




print("Owner gives access to private lenses")
owner      = users.get(username='Cameron')
other_user = users.get(username='Giorgos')
some_group = SledGroups.objects.get(name="Awesome Users")
print(owner,other_user,some_group)

private_lenses = Lenses.accessible_objects.all(owner).filter(access_level='private')

# simplest way: loop and give access object by object
# for i in range(0,3):
#     owner.giveAccess(private_lenses[i],other_user)
# for i in range(6,10):
#     owner.giveAccess(private_lenses[i],some_group)
# accessible_objects_per_user()

# object list: give access for a list of objects to user or group
# owner.giveAccess(private_lenses[0:3],other_user)
# owner.giveAccess(private_lenses[6:10],some_group)
# accessible_objects_per_user()

# most compact way: give access to a list of objects to a list of users/groups
notifications = owner.giveAccess(private_lenses[0:3],[other_user])
notifications = owner.giveAccess(private_lenses[6:10],[some_group])
for note in notifications:
    print(note)
accessible_objects_per_user()
print()



print("Owner revokes access to private lenses")
notifications = owner.revokeAccess(private_lenses[0:3],[other_user])
for note in notifications:
    print(note)
accessible_objects_per_user()
print()




# owner.revokeAccess(private_lenses[0],other_user)
# for i in range(0,3):
#     owner.revokeAccess(private_lenses[i],other_user)
# for i in range(6,10):
#     owner.revokeAccess(private_lenses[i],some_group)
# accessible_objects_per_user()
# print()

# print("Owner revokes access to public lenses")
# public_lenses = Lenses.accessible_objects.all(owner).filter(access_level='public')
# owner.revokeAccess(public_lenses[0],other_user)
# accessible_objects_per_user()
# print()
