import sys
import os
import django
from django.db.models import Max, Subquery, Q

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Lenses,Imaging

#test = Imaging.objects.filter(Q(exists=True) & Q(exposure_time__gt=1.01) & Q(exposure_time__lte=150))
#print('test: ',len(test))

#dum = Lenses.objects.filter(imaging__instrument__name__contains='Pan').filter( Q(imaging__exists=True) ).distinct()
#print(len(dum))


pan = Lenses.objects.filter( Q(imaging__exists=True) & Q(imaging__instrument__name__contains='Pan') ).distinct()
print('panstars: ',len(pan))
lsn = Lenses.objects.filter( Q(imaging__exists=True) & Q(imaging__instrument__name__contains='North') ).distinct()
print('Legacy survey north: ',len(lsn))
lss = Lenses.objects.filter( Q(imaging__exists=True) & Q(imaging__instrument__name__contains='South') ).distinct()
print('Legacy survey south: ',len(lss))


both = set(pan).intersection(set(lsn))
print('Pan AND North: ',len(both))

both = set(pan).intersection(set(lss))
print('Pan AND South: ',len(both))

both = set(lsn).intersection(set(lss))
print('North AND South: ',len(both))

all = set(lsn).intersection(set(lss),set(pan))
print('North AND South AND Panstars: ',len(all))



both = set(lsn).union(set(lss))
print('North OR South: ',len(both))



#ids = [lens.id for lens in set(lsn).intersection(set(lss))]
conditions = Q(imaging__exists=True) & Q(imaging__exposure_time__gte=0.5) & Q(imaging__exposure_time__lte=900)
test1 = Lenses.objects.filter( conditions & Q(imaging__instrument__name__contains='North') ).distinct()
test2 = Lenses.objects.filter( conditions & Q(imaging__instrument__name__contains='South') ).distinct()
test3 = Lenses.objects.filter( conditions & Q(imaging__instrument__name__contains='Pan') ).distinct()
print(len(test1),len(test2),len(test3))
final = set(test1).intersection(set(test2))
print('North AND South AND Panstars with conditions: ',len(final))
