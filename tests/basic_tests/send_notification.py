import os
import sys
import django

base_dir = '../../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

# -----------------------------------------------------


from lenses.models import Users, SledGroups, Lenses
from notifications.signals import notify

actor = Users.objects.get(username='Cameron')

#print('hello')
notify.send(actor, recipient=actor, verb='you reached level 10')
