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

from lenses.models import Users, Lenses, Imaging, Spectrum, Catalogue
from guardian.shortcuts import assign_perm

from actstream import action
from actstream.registry import register
register(Imaging,Spectrum,Catalogue)



print('Changing the ownership of some data for testing purposes')

user = Users.objects.filter(username='gvernard')
admin = Users.objects.get(username='admin')

imagings = Imaging.objects.filter(exists=True).order_by('?')[:113]
print(len(imagings))
spectra = Spectrum.objects.filter(exists=True).order_by('?')[:73]
print(len(spectra))
cats = Catalogue.objects.filter(exists=True).order_by('?')[:123]
print(len(cats))


#admin.cedeOwnership(imagings,user,'comme imag')
admin.cedeOwnership(spectra,user,'comme spec')
admin.cedeOwnership(cats,user,'comme cata')



