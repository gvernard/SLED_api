import sys
import os
import django
from random import randrange

base_dir = '../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lensdb.models import Users, Lenses
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import get_users_with_perms

from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np

usernames = ['Cameron', 'Giorgos', 'Fred']
for username in usernames:
    user = Users.objects.get(username=username)
    #q = Lenses.objects.filter(ra__gte=180)
    #accessible_lenses = get_objects_for_user(user, 'has_access', klass=q)
    accessible_lenses = get_objects_for_user(user, 'lensdb.view_lenses',)
    print(username+' has access to '+str(len(accessible_lenses))+' lenses')


lenses = Lenses.objects.all()

N = len(lenses)
#index = randrange(N)
index = 43
lens = lenses[index]
print('The following have access to this lens:', index, get_users_with_perms(lens))
