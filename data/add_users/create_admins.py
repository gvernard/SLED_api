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

from lenses.models import Users, SledGroup, Lenses, SingleObject, Collection
from guardian.shortcuts import assign_perm

from actstream import action
from actstream.registry import register
register(Users)

admin1 = Users.objects.get(username='gvernard')
admin2 = Users.objects.get(username='Cameron')

admin1.is_staff = True
admin2.is_staff = True

admin1.save()
admin2.save()

