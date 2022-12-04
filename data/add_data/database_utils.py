import os
import datetime

import requests
from requests.auth import HTTPBasicAuth

import sys
sys.path.append('../../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

import django
django.setup()

from django.conf import settings
from lenses.models import Catalogue, Imaging, Spectrum, Instrument, Band, Users, Lenses
from api.serializers import ImagingDataUploadSerializer
from django.db.models import Q, F, Func, FloatField, CheckConstraint
from django.utils.timezone import make_aware

def match_to_lens(ra, dec):
    qset = Lenses.objects.all().annotate(distance=Func(F('ra'),F('dec'),ra,dec,function='distance_on_sky',output_field=FloatField())).filter(distance__lt=10.)
    if qset.count() > 0:
        return qset
    else:
        return False



def upload_data_to_db_API(datalist, datatype, username, password):
    """
    datalist: list of json files containing the neccessary metadata for the Imaging table
    this function goes through the API, and requires confirmation
    datatype: one of 'Imaging', 'Spectrum', 'Catalogue'
    username, password: strings
    """
    url = "http://127.0.0.1:8000/api/upload-data/"

    form_data = [
       ('N', ('',str(len(datalist)))),
       ('type', ('',datatype))
    ]
    for datum in datalist:
       dum = []
       for key in datum.keys():
          if key != 'image':
            if datum[key]==None:
                dum.append( (key,('','')) )
            else:
                dum.append( (key,('',str(datum[key]))) )
          else:
             dum.append( ('image',open(datum[key],'rb')) )
       form_data.extend(dum)

    r = requests.post(url,files=form_data,auth=HTTPBasicAuth(username, password))

    if r.ok:
        print("Upload completed successfully!")
    else:
        print("Something went wrong!")
    #print(r.text)
    return 0



def upload_imaging_to_db_direct(datalist, username):
    """
    datalist: list of json files containing the neccessary metadata for the Imaging table
    this function creates objects directly in the database; to be used by automatic uploads
    """
    for data in datalist:
        finaldata = data.copy()

        path = settings.MEDIA_ROOT + '/temporary/admin/'
        if not os.path.exists(path):
            os.makedirs(path)

        print(data)
        #check if the data exists and therefore should have an image
        if data['exists']:
            if '/' in data['image']:
                savename = data['image'].split('/')[-1]
            else:
                savename = data['image']

            with open(path + savename,'wb+') as destination:
                destination.write(open(data['image'],'rb').read())

        finaldata['instrument'] = Instrument.objects.get(name=data['instrument'])
        finaldata['band'] = Band.objects.get(name=data['band'])
        #indices,neis = Lenses.proximate.get_DB_neighbours_anywhere_many([data['ra']], [data['dec']])
        lens = match_to_lens(data['ra'], data['dec'])

        finaldata['lens'] = lens[0]
        finaldata.pop('ra')
        finaldata.pop('dec')

        imaging = Imaging(**finaldata)

        imaging.owner_id = Users.objects.get(username=username).id
        if data['exists']:
            imaging.image.name = '/temporary/admin/' + savename
        if 'date_taken' in finaldata.keys():
            imaging.date_taken = make_aware(datetime.datetime.fromisoformat(finaldata['date_taken']))
        imaging.save()

    return None

def upload_spectrum_to_db_direct(datalist, username):

    for data in datalist:

        finaldata = data.copy()

        path = settings.MEDIA_ROOT + '/temporary/admin/'
        if not os.path.exists(path):
            os.makedirs(path)

        print(data)
        if data['exists']:
            if '/' in data['image']:
                savename = data['image'].split('/')[-1]
            else:
                savename = data['image']

            with open(path + savename,'wb+') as destination:
                destination.write(open(data['image'],'rb').read())

        finaldata['instrument'] = Instrument.objects.get(name=data['instrument'])
        lens = match_to_lens(float(data['ra']), float(data['dec']))

        finaldata['lens'] = lens[0]
        finaldata.pop('ra')
        finaldata.pop('dec')


        spectrum = Spectrum(**finaldata)
        spectrum.owner_id = Users.objects.get(username=username).id
        if data['exists']:
            spectrum.image.name = '/temporary/admin/' + savename
        if 'date_taken' in finaldata.keys():
            spectrum.date_taken = make_aware(datetime.datetime.fromisoformat(finaldata['date_taken']))
        spectrum.save()
    return 0

def upload_catalogue_to_db_direct(datalist, username):

    for data in datalist:

        finaldata = data.copy()

        finaldata['instrument'] = Instrument.objects.get(name=data['instrument'])
        finaldata['band'] = Band.objects.get(name=data['band'])
        lens = match_to_lens(float(data['radet']), float(data['decdet']))

        finaldata['lens'] = lens[0]
        finaldata.pop('ra')
        finaldata.pop('dec')
        catalogue = Catalogue(**finaldata)
        catalogue.owner_id = Users.objects.get(username=username).id
        if 'date_taken' in finaldata.keys():
            catalogue.date_taken = make_aware(datetime.datetime.fromisoformat(finaldata['date_taken']))
        catalogue.save()
    return 0