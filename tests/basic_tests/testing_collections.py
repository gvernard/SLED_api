import sys
import os
import django

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, Lenses, Collection
from django.contrib.auth.models import User


# A user to own the collection
sled_user = Users.objects.get(username='gvernard')


col = Collection.objects.get(pk=1)
print(col.myitems.all())

# # Some public lenses to add to the collection
# pub = Lenses.objects.filter(access_level='PUB')[:4]
# print(pub.values('id'))

# mycollection = Collection(owner=sled_user,name="TheBest",description="The best collection of lenses to walk the earth.",item_type="Lenses")
# mycollection.save()
# mycollection.myitems = pub
# mycollection.save()

# print(mycollection)
# print(mycollection.myitems)
# for item in mycollection.myitems:
#     print(item)




