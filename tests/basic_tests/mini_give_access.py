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

from lenses.models import Users, SledGroups, Lenses, SingleObject
from guardian.shortcuts import assign_perm


owner  = Users.objects.get(username='gvernard')

mylenses = []
for i in range(1,8):
    lens = Lenses(ra=i,dec=i,owner=owner)
    lens.create_name()
    if i < 6:
        lens.access_level = SingleObject.AccessLevel.PRIVATE
    else:
        lens.access_level = SingleObject.AccessLevel.PUBLIC        
    mylenses.append( lens )

Lenses.objects.bulk_create(mylenses)
mylenses = Lenses.objects.all()
pri = []
for lens in mylenses:
    if lens.access_level == 'PRI':
        pri.append(lens)
if pri:
    assign_perm('view_lenses',owner,pri)



private_lenses = Lenses.objects.filter(owner=owner).filter(access_level='PRI')

other_user  = Users.objects.get(username='Cameron')
other_user2 = Users.objects.get(username='Fred')
some_group  = SledGroups.objects.get(name="Awesome Users")
some_group2 = SledGroups.objects.get(name="TDCOSMO")

owner.giveAccess(private_lenses[0],[other_user,other_user2])
owner.giveAccess(private_lenses[1],[other_user])
owner.giveAccess(private_lenses[2],[other_user2])
owner.giveAccess(private_lenses[3],[other_user,some_group2])
owner.giveAccess(private_lenses[4],[other_user2,some_group,some_group2])
