import sys
import os
import django

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../../')
sys.path.append(base_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Instrument, Band
import json                    
from django.core.exceptions import ValidationError


f = open('instruments.json')
instruments = json.load(f)
f.close()
for instrument in instruments:
    instr = Instrument(name=instrument["name"],info=instrument["info"])
    try:
        instr.full_clean()
    except ValidationError as e:
        print(instr.name,e)
    else:
        instr.save()



f = open('bands.json')
bands = json.load(f)
f.close()
for band in bands:
    b = Band(name=band["name"],info=band["info"])
    try:
        b.full_clean()
    except ValidationError as e:
        print(b.name,e)
    else:
        b.save()
