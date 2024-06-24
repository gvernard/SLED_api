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



from lenses.models import Lenses, Users, Redshift


path = '/var/www/sled/SLED_api/scripts/'


user = Users.objects.get(username='Giorgos')

seps = Lenses.objects.filter(flag='CONFIRMED').filter(image_sep__gt=0.01).values_list('image_sep',flat=True)
np.savetxt(path+'separations.dat',seps)

z_lens = Redshift.objects.filter(tag='LENS').filter(lens__flag='CONFIRMED').values_list('value',flat=True)
np.savetxt(path+'z_lens.dat',z_lens)

z_source = Redshift.objects.filter(tag='SOURCE').filter(lens__flag='CONFIRMED').values_list('value',flat=True)
np.savetxt(path+'z_source.dat',z_source)
