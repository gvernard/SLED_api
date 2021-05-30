import sys
import os
import django

base_dir = '../'
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lensdb.models import Users, Groups, Lenses
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm


user1 = Users.objects.get(username='Cameron')
user2 = Users.objects.get(username='Giorgos')
group1 = Groups.objects.get(name="Awesome Users")

all_lenses = Lenses.objects.all()
for i, lens in enumerate(all_lenses):
    if i < 20:
        #assign_perm('has_access', user1, lens)
        assign_perm('view_lenses', user1, lens)
        print('Giving access to ', lens.name, 'to ', user1.username)
    if i > 89:
        #assign_perm('has_access', user2, lens)
        assign_perm('view_lenses', user2, lens)
        print('Giving access to ', lens.name, 'to ', user2.username)
        #print(user2.has_perm('has_access', lens))
    if 40 < i and i < 45:
        assign_perm('view_lenses', group1, lens)
        print('Giving access to ', lens.name, 'to ', group1.name)
        
