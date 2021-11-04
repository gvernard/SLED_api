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


# Some public lenses to add to the collection
pub = Lenses.objects.filter(access_level='PUB').order_by('ra')[4:8]



mycollection = Collection(owner=geo,name="TheBest",description="The best collection of lenses to walk the earth.",item_type="Lenses")
mycollection.save()
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
task = ConfirmationTask.objects.get(pk=1)
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


