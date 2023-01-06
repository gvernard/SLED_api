import sys
import os
sys.path.append('../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django
django.setup()

from lenses.models import Users, SledQuery

admin = Users.objects.get(username='admin')

names, descriptions, query_details = [], [], []

#LENSED QUASARS
name = 'Lensed quasars'
description = 'All confirmed lenses with quasar sources'
query_detail = {'source_type':'QUASAR', 'flag_confirmed':True}
names.append(name)
descriptions.append(description)
query_details.append(query_detail)

#QUADS
name = 'Quadruply-imaged lensed quasars'
description = 'All confirmed lensed quasars with four or more images'
query_detail = {'source_type':'QUASAR', 'flag_confirmed':True, 'n_img_min':4}
names.append(name)
descriptions.append(description)
query_details.append(query_detail)


#DOUBLES
name = 'Doubly-imaged lensed quasars'
description = 'All confirmed lensed quasars with 2 images'
query_detail = {'source_type':'QUASAR', 'flag_confirmed':True, 'n_img_min':2, 'n_img_max':2}
names.append(name)
descriptions.append(description)
query_details.append(query_detail)

#TRIPLES
name = 'Triply-imaged lensed quasars'
description = 'All confirmed lensed quasars with 3 images'
query_detail = {'source_type':'QUASAR', 'flag_confirmed':True, 'n_img_min':3, 'n_img_max':3}
names.append(name)
descriptions.append(description)
query_details.append(query_detail)



#z>4 lensed quasars
name = 'z>4 lensed quasars'
description = 'All confirmed lensed quasars with source redshifts above z=4'
query_detail = {'source_type':'QUASAR', 'flag_confirmed':True, 'z_source_min':4}
names.append(name)
descriptions.append(description)
query_details.append(query_detail)



#LENSED GALAXIES
name = 'Lensed galaxies'
description = 'All confirmed lenses with galaxy sources'
query_detail = {'source_type':'GALAXY', 'flag_confirmed':True}
names.append(name)
descriptions.append(description)
query_details.append(query_detail)


#LENSED GALAXIES
name = 'Lensed supernovae'
description = 'All confirmed lenses with supernovae sources'
query_detail = {'source_type':'SN', 'flag_confirmed':True}
names.append(name)
descriptions.append(description)
query_details.append(query_detail)



for i in range(len(names)):
    name, description, query_detail = names[i], descriptions[i], query_details[i]    
    q = SledQuery(owner=admin, name=name, description=description, access_level='PUB')
    cargo = q.compress_to_cargo(query_detail)

    q.cargo = cargo
    q.save()