import sys
import os
import django

base_dir = '../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lensdb.models import Users, Lenses
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm


user1 = Users.objects.get(username='Cameron')
user2 = Users.objects.get(username='Giorgos')

all_lenses = Lenses.objects.all()
for i, lens in enumerate(all_lenses):
    if i < 50:
        assign_perm('has_access', user1, lens)
        print('Giving access to ', lens.name, 'to ', user1.username)
    if i > 79:
        assign_perm('has_access', user2, lens)
        print('Giving access to ', lens.name, 'to ', user2.username)
        #print(user2.has_perm('has_access', lens))