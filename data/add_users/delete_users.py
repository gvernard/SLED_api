import sys
import os
import django
from random import randrange

from django.db.models import Count

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, Lenses, Imaging, Spectrum, Catalogue
from guardian.shortcuts import assign_perm


duplicate_email = Users.objects.values('email').order_by().annotate(email_count=Count('email')).filter(email_count__gt=1)
print(duplicate_email)

qset = Users.objects.filter(email__in=[item['email'] for item in duplicate_email]).filter(is_active=True).exclude(username='PPR50')
print(qset)

#qset.delete()
