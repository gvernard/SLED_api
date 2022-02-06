import sys
import os
import django
from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np
from astropy.table import Table

dirname = os.path.dirname(__file__)
base_dir = os.path.join(dirname,'../')
sys.path.append(base_dir)

#Database init
os.environ['DJANGO_SETTINGS_MODULE'] = "mysite.settings"
django.setup()

from lenses.models import Users, SledGroup, Lenses, SingleObject
from django.forms.models import model_to_dict
from guardian.shortcuts import assign_perm

user1 = Users.objects.get(username='Cameron')

# Adding lenses
print('Populating the database with known lensed quasars')
data = Table.read('./trial_sample/lensed_quasars_uploadtable.fits')

# for i in range(0,len(data['separation'])):
#     if float(data['separation'][i]) > 20 or float(data['separation'][i]) < 0:
#         print(data['separation'][i])

ras, decs = data['RA'], data['DEC']
names = data['Name']
z_source, z_lens = data['z_qso'], data['z_lens']
nimg = data['N_images']
separation = data['separation']
confirmed = data['confirmed']
access = data['access']

lensedquasars = []
for i in range(len(ras)):
    lens = Lenses(ra=ras[i], dec=decs[i], owner=user1)
    lens.name = names[i]
    #lens.create_name()
    lens.n_img = nimg[i]
    lens.flag_confirmed = confirmed[i]
    lens.image_sep = separation[i]
    try:
        z_s = float(z_source[i])
        lens.z_source = z_s
    except Exception:
        pass
    try:
        z_l = float(z_lens[i])
        lens.z_lens = z_l
    except Exception:
        pass
    if access[i]=='PRI':
        lens.access_level = SingleObject.AccessLevel.PRIVATE
    elif access[i]=='PUB':
        lens.access_level = SingleObject.AccessLevel.PUBLIC

    lens.mugshot_name = names[i]+'.png'
    lens.source_type = 'QUASAR'
    lens.lens_type = 'GALAXY'
    if names[i] in ['SDSSJ1004+4112', 'SDSSJ1029+2623', 'J1325+4806', 'SDSSJ2222+2745']:
        lens.lens_type = 'CLUSTER'

    if names[i] in ['DESJ0340-2545', 'Q0957+561', 'SDSSJ0909+4449']:
        lens.lens_type = 'GROUP'

    if '*' in names[i]:
        lens.flag_confirmed = False

    if lens.n_img==2:
        lens.image_conf = 'DOUBLE'
    if lens.n_img==4:
        lens.image_conf = 'QUAD'

    #copy the image to the relevant place
    #os.system('cp ./trial_sample/images/'+names[i]+'.png ./lenses/static/lenses/mugshots/')
    
    lensedquasars.append( lens )
    
Lenses.objects.bulk_create(lensedquasars)
lensedquasars = Lenses.objects.all()
assign_perm('view_lenses', user1, lensedquasars)


for lens in lensedquasars:
    fname = 'upload_'+str(lens.id) + '.png'
    os.system('cp ./trial_sample/images/'+lens.name+'.png ./media/lenses/' + fname)
    lens.mugshot.name = 'lenses/' + fname
    lens.save()




#lenses = Lenses.objects.all()

