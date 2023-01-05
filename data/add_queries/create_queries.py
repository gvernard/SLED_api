import sys
import os
sys.path.append('../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django
django.setup()

from lenses.models import Users, SledQuery

admin = Users.objects.get(username='admin')

query_details = {'ra_min':0, 'ra_max':10, 'source_type':'QUASAR'}

name = 'test_query'
description = 'Query for testing'
q = SledQuery(owner=admin, name=name, description=description, access_level='PUB')
cargo = q.compress_to_cargo(query_details)

q.cargo = cargo
q.save()