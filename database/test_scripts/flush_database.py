import sys
import os
import django

base_dir = '../'
sys.path.append(base_dir)


#from django.core.management import call_command
#call_command('flush', '--noinput')


#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lensdb.models import Users, SledGroups, Lenses
from django.db.models import Q

users = Users.objects.filter(~Q(username='admin'))
users.delete()

lenses = Lenses.objects.all().delete()

groups = SledGroups.objects.all().delete()

