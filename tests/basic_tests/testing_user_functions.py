import sys
import os
import django
from random import randrange

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, SledGroups, Lenses, ConfirmationTask
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import get_users_with_perms

from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np


###### Do some initialization
#users = Users.objects.exclude(username='admin')
users = Users.objects.all()

def accessible_objects_per_user():
    print("Accessible objects per user: ")
    users = Users.objects.exclude(username='admin')
    for user in users:
        lenses = Lenses.accessible_objects.all(user)
        print(user.username,len(lenses))
    print()

    
def owned_objects_per_user():
    print("Owned objects per user: ")
    users = Users.objects.exclude(username='admin')
    for user in users:
        owned_objects = user.getOwnedObjects(["Lenses","dummy"])
        for key in owned_objects:
            print(user.username,key,len(owned_objects[key]))
    print()

def groups_per_user():
    print("Groups that user belongs to: ")
    users = Users.objects.exclude(username='admin')
    for user in users:
        groups = user.getGroupsIsMember()
        print(user.username,groups.values_list('name',flat=True))
    print()
    
owned_objects_per_user()
groups_per_user()
accessible_objects_per_user()
#############################







########### FIRST TEST
print("TEST ==== Owner gives access to private lenses")
owner       = users.get(username='Cameron')
other_user  = users.get(username='Giorgos')
other_user2 = users.get(username='Fred')
some_group  = SledGroups.objects.get(name="Awesome Users")
other_group = SledGroups.objects.get(name="TDCOSMO")

private_lenses = Lenses.accessible_objects.all(owner).filter(access_level='PRI')

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
owner.giveAccess(private_lenses[0:3],[other_user,other_user2])
owner.giveAccess(private_lenses[4],[other_user])
owner.giveAccess(private_lenses[6:10],[some_group])
owner.giveAccess(private_lenses[11:13],[other_group])

accessible_objects_per_user()
print()
########################





########### ANOTHER TEST
print("TEST ==== Owner makes some private lenses public")
#public_lenses = Lenses.accessible_objects.all(owner).filter(access_level='PUB')

owner = users.get(username='Cameron')
private_lenses = Lenses.accessible_objects.all(owner).filter(access_level='PRI')
print("User ",owner," has ",len(private_lenses)," private objects")


ids = [private_lenses[i].id for i in range(20,25)]
#print(ids)
set1 = Lenses.objects.filter(pk__in=ids)
for i in range(0,set1.count()):
    print(set1[i],get_users_with_perms(set1[i],only_with_perms_in=['view_lenses']))
    
owner.makePublic(list(private_lenses[20:25]))

private = Lenses.accessible_objects.all(owner).filter(access_level='PRI')
print("User ",owner," has ",len(private)," private objects")
for i in range(0,set1.count()):
    print(set1[i],get_users_with_perms(set1[i],only_with_perms_in=['view_lenses']))

accessible_objects_per_user()
print()

########################




########### ANOTHER TEST
print("TEST ==== Owner cedes ownesrhip to another user")

# Test for user ownership
owned_objects_per_user()

# Owner selects some objects to cede to another user (receiver)
sender = users.get(username='Cameron')
receiver = users.filter(username='Giorgos')
owned_lenses = sender.getOwnedObjects(["Lenses","dummy"])
lenses_to_cede = owned_lenses["Lenses"][3:6]
print("Lenses to cede from ",sender," to ",receiver,":",lenses_to_cede)
print()
mytask = sender.cedeOwnership(lenses_to_cede,receiver)

# Receiver accepts
target_receiver = users.get(username='Giorgos')
mytask.registerAndCheck(target_receiver,'yes','I will happily take over.')

# Test for user ownership
owned_objects_per_user()
########################




########### ANOTHER TEST
print("TEST ==== Owner makes some public lenses private")

# Owner selects some objects to make private
owner = users.get(username='Cameron')
public_lenses = Lenses.objects.filter(owner=owner,access_level='PUB')
private_lenses = Lenses.objects.filter(owner=owner,access_level='PRI')

# Test for AccessLevel
print(owner,"'s PUBLIC lenses: ",public_lenses.count())
print(owner,"'s PRIVATE lenses: ",private_lenses.count())

lenses_to_privatize = public_lenses[3:6]
print("Lenses to privatize:",lenses_to_privatize)
print()
mytask = sender.makePrivate(lenses_to_privatize)

# Admin accepts
target_receiver = users.get(username='admin')
mytask.registerAndCheck(target_receiver,'yes','You can make these lenses private.')

# Test for AccessLevel
public_lenses = Lenses.objects.filter(owner=owner,access_level='PUB')
private_lenses = Lenses.objects.filter(owner=owner,access_level='PRI')
print(owner,"'s PUBLIC lenses: ",public_lenses.count())
print(owner,"'s PRIVATE lenses: ",private_lenses.count())
print()
########################




########### ANOTHER TEST
print("TEST ==== Owner revokes access to private lenses")
owner = users.get(username='Cameron')
private_lenses = Lenses.objects.filter(owner=owner,access_level='PRI')

print('BEFORE:')
set_with_perms = []
for i in range(0,private_lenses.count()):
    qset = get_users_with_perms(private_lenses[i],only_with_perms_in=['view_lenses'])
    if qset.count() > 1:
        set_with_perms.append(private_lenses[i])
        print(private_lenses[i],qset)


other_user = users.get(username='Giorgos')
other_user2 = users.get(username='Fred')
some_group  = SledGroups.objects.get(name="Awesome Users")
some_group2  = SledGroups.objects.get(name="TDCOSMO")

# Comment and uncomment any combinations of lines below to see the effect
#owner.revokeAccess(set_with_perms[0],[other_user])
#owner.revokeAccess(set_with_perms[1],[other_user2])
#owner.revokeAccess(set_with_perms[2],[other_user,other_user2])
#owner.revokeAccess(set_with_perms,[some_group])
owner.revokeAccess(set_with_perms,[other_user,some_group2])


print('AFTER:')
for i in range(0,len(set_with_perms)):
    qset = get_users_with_perms(set_with_perms[i],only_with_perms_in=['view_lenses'])
    print(set_with_perms[i],qset)


print()
########################


