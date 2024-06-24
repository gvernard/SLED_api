import os
import sys
import django
from django.contrib.sites.models import Site

from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np

dirname = os.path.dirname(__file__)
sys.path.append(dirname)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Lenses



user = Users.get(username='Giorgos')

lenses = Lenses.accessible_objects.all(user).filter(flag='Confirmed')
print(len(lenses))
