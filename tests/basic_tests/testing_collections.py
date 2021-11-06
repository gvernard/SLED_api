import sys
import os
import django

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, Lenses, Collection, ConfirmationTask
from django.contrib.auth.models import User


# A user to own the collection
geo = Users.objects.get(username='gvernard')
fre = Users.objects.get(username='Fred')
cam = Users.objects.get(username='Cameron')





'''
############################# Testing a public collection #############################
mycollection = Collection(owner=geo,name="TheBest",access_level='PUB',description="The best collection of lenses to walk the earth.",item_type="Lenses")
mycollection.save()
pub = Lenses.objects.filter(access_level='PUB').order_by('ra')[4:8]
mycollection.myitems = pub
mycollection.save()
print(mycollection.myitems.all())


# Check 1: the user is trying to add objects is not the owner of the collection
print('Check 1:')
pub2 = Lenses.objects.filter(access_level='PUB').order_by('ra')[8:10]
ret = mycollection.addItems(cam,list(pub2))
print(ret)


# Check 2: trying to add wrong item types, e.g. Users.
print('Check 2:')
ret = mycollection.addItems(geo,[fre])
print(ret)
task = ConfirmationTask.create_task(geo,Users.getAdmin(),'MakePrivate',{})
ret = mycollection.addItems(geo,task)
print(ret)


# Check 3: some items are already in the collection.
print('Check 3:')
pub3 = Lenses.objects.filter(access_level='PUB').order_by('ra')[6:9]
ids = list(pub3.values_list('id',flat=True))
ret = mycollection.addItems(geo,pub3)
print(ret)


# Check 4: all new items are public
print('Check 4:')
pub4 = Lenses.objects.filter(access_level='PUB').order_by('ra')[10:11]
print(pub4)
ret = mycollection.addItems(geo,pub4)
print(ret)
print(mycollection.myitems.all())


# Check 5: try to add private objects to a public collection
pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[:5]
print('Owner: ',pri.values_list('owner__username',flat=True))
print('Users with access:')
for obj in pri:
    print(obj,obj.getUsersWithAccess(cam))
ret = mycollection.addItems(geo,pri)
print(ret)
'''



############################# Testing a private collection #############################
mycollection = Collection(owner=geo,name="Worst",access_level='PRI',description="Aliens invaded earth in 2019 in the form of a virus.",item_type="Lenses")
mycollection.save()
pub = Lenses.objects.filter(access_level='PUB').order_by('ra')[4:8]
mycollection.myitems = pub
mycollection.save()
print(mycollection.myitems.all())


# Check 1: try to add private objects without having access to them
print('Check 1:')
pri = Lenses.objects.filter(access_level='PRI').order_by('ra')[:1]
print('Owner: ',pri.values_list('owner__username',flat=True))
print('Users with access:')
for obj in pri:
    print(obj,obj.getUsersWithAccess(cam))
ret = mycollection.addItems(geo,pri)
print(ret)

