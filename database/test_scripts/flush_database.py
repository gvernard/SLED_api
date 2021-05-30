import sys
import os
import django

base_dir = '../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lensdb.models import Users, Groups, Lenses
from django.db.models import Q

users = Users.objects.filter(~Q(username='admin'))
users.delete()

lenses = Lenses.objects.all().delete()

groups = Groups.objects.all().delete()
