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

from lenses.models import Users, SledGroup, Lenses, SingleObject
from guardian.shortcuts import assign_perm


owner  = Users.objects.get(username='gvernard')
mugshot_path = base_dir+'tests/test_mugshots/'

mylenses = []
for i in range(1,7):
    lens = Lenses(ra=i,dec=i,owner=owner)
    lens.create_name()
    if i < 6:
        lens.access_level = SingleObject.AccessLevel.PRIVATE
    else:
        lens.access_level = SingleObject.AccessLevel.PUBLIC

    fname = 'upload_'+str(lens.id) + '.png'
    lens_fname = 'lens'+str(i)+'.png'
    cpstr = 'cp ' + mugshot_path + lens_fname + ' ' + base_dir + 'media/lenses/' + fname
    os.system('cp ' + mugshot_path + lens_fname + ' ' + base_dir + '/media/lenses/' + fname)
    lens.mugshot.name = 'lenses/' + fname
    lens.save()
    mylenses.append( lens )


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
some_group  = SledGroup.objects.get(name="Awesome Users")
some_group2 = SledGroup.objects.get(name="TDCOSMO")

owner.giveAccess(private_lenses[0],[other_user,other_user2])
owner.giveAccess(private_lenses[1],[other_user])
owner.giveAccess(private_lenses[2],[other_user2])
owner.giveAccess(private_lenses[3],[other_user,some_group2])
owner.giveAccess(private_lenses[4],[other_user2,some_group,some_group2])
