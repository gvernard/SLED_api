from __future__ import absolute_import
import os
import time
import base64
from datetime import timedelta

from celery import Celery
from celery import shared_task
from celery.schedules import crontab

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.template.loader import get_template
from django.utils.html import strip_tags
from django.core.files.base import ContentFile
from django.forms import inlineformset_factory
from django.core import serializers

from actstream import action

from sled_lens_models.utils import extract_coolest_info_2




os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

app = Celery('mysite')
app.config_from_object('django.conf:settings',namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
#app.autodiscover_tasks()
app.conf.timezone = 'America/New_York'







@app.task
def my_divide(x,y):
    import time
    time.sleep(5)
    return x / y

@app.task
def my_periodic_task(arg1, arg2):
    print(f"Running periodic task with args: {arg1}, {arg2}")
    # Add your task logic here

 
@shared_task
def celery_save_lens_model(lens_model_id,tar_path):
    model_ref = apps.get_model(app_label='lenses',model_name='LensModels')
    lens_model = model_ref.objects.get(id=lens_model_id)
    
    try:
        with default_storage.read_tar(tar_path) as tar:
            r_eff_source,einstein_radius,masses,lights,source,free_pars,buf_dmr,buf_corner = extract_coolest_info_2(tar)

        lens_model.lens_mass_model = masses
        lens_model.lens_light_model = lights
        lens_model.source_light_model = source
        lens_model.r_eff_source = r_eff_source
        lens_model.einstein_radius = einstein_radius
        dmr_fname = lens_model.coolest_file.field.upload_to + str(lens_model.id) + "_pngs/" + str(lens_model.id) + "_dmr_plot.png"
        corner_fname = lens_model.coolest_file.field.upload_to + str(lens_model.id) + "_pngs/" + str(lens_model.id) + "_corner_plot.png"
        default_storage.put_object(buf_dmr.read(),dmr_fname)
        default_storage.put_object(buf_corner.read(),corner_fname)
        
    except Exception as e:
        raise ValidationError(f"Failed to process COOLEST file: {e}")
    
    lens_model.save()






    
@shared_task
def celery_upload_lenses(user_id,lenses):
    from django.contrib.sites.models import Site
    from guardian.shortcuts import assign_perm
    from lenses import forms

    users_ref = apps.get_model(app_label='lenses',model_name='Users')
    lenses_ref = apps.get_model(app_label='lenses',model_name='Lenses')
    tasks_ref = apps.get_model(app_label='lenses',model_name='ConfirmationTask')
    user = users_ref.objects.get(id=user_id)
    from_email = 'sled-no-reply@sled.amnh.org'
    recipient_email = user.email
    mycontext = {
        'first_name': user.first_name,
    }

    ras = []
    decs = []
    instances = []
    for lens in lenses:
        lens_obj = lenses_ref(**lens)
        lens_obj.owner = user
        instances.append(lens_obj)
        ras.append(lens["ra"])
        decs.append(lens["dec"])

    indices, neis = lenses_ref.proximate.get_DB_neighbours_anywhere_many(ras,decs,user=user)
    if len(indices) == 0:
        pri = []
        pub = []

        for lens in instances:
            if lens.access_level == 'PRI':
                pri.append(lens)
            else:
                lens.access_level = 'PRI'
                pub.append(lens)
            lens.full_clean()
            lens.save()

        assign_perm('view_lenses', user, instances)

        if pub:
            object_type = pub[0]._meta.model.__name__
            cargo = {
                'object_type': object_type,
                'object_ids': [lens.id for lens in pub],
            }
            receiver = users_ref.selectRandomInspector()
            mytask = tasks_ref.create_task(user, receiver, 'InspectImages', cargo)

        # Send email
        subject = 'SLED: Lenses successfully uploaded'
        html_message = get_template('emails/uploading_lenses_success.html')
        mycontext['N_pri'] = len(pri)
        mycontext['N_pub'] = len(pub)
        html_message = html_message.render(mycontext)
        plain_message = strip_tags(html_message)
        send_mail(subject,plain_message,from_email,[recipient_email],html_message=html_message)
        
        # Remove files uploaded to user's temporary directory
        for lens in instances:
            tmp_fname = f'temporary/{user.username}/{lens.mugshot.name}'
            default_storage.mydelete(tmp_fname)
        
    else:
        cargo = {'mode': 'add', 'objects': serializers.serialize('json', instances)}
        receiver = users_ref.objects.filter(id=user.id)
        mytask = tasks_ref.create_task(user, receiver, 'ResolveDuplicates', cargo)
        current_site = Site.objects.get_current()
        task_url = f"https://{current_site.domain}{mytask.get_absolute_url()}"
        
        # Send email
        subject = 'SLED: Lenses uploaded but duplicates were identified'
        html_message = get_template('emails/uploading_lenses_duplicates.html')
        mycontext["url"] = task_url
        html_message = html_message.render(mycontext)
        plain_message = strip_tags(html_message)
        send_mail(subject,plain_message,from_email,[recipient_email],html_message=html_message)

    
    
    
@shared_task
def celery_upload_papers(user_id,paper):
    #from api.serializers import PapersSerializer, PaperUploadSerializer

    ad_col_ref = apps.get_model(app_label='lenses',model_name='AdminCollection')
    papers_ref = apps.get_model(app_label='lenses',model_name='Paper')
    users_ref = apps.get_model(app_label='lenses',model_name='Users')
    lenses_ref = apps.get_model(app_label='lenses',model_name='Lenses')
    user = users_ref.objects.get(id=user_id)

    # Match RA,DEC to lenses and check for duplicates/no matches
    errors = []

    lenses = paper.pop('lenses')
    for i,lens in enumerate(lenses):
        ra  = lenses[i].pop('ra')
        dec = lenses[i].pop('dec')
        qset = lenses_ref.proximate.get_DB_neighbours_anywhere(ra,dec)
        N = qset.count()
        if N == 0:
            errors.append('RA,dec = (%f,%f) -- no lens found at these coordinates!' % (ra,dec))
        elif N > 1: 
            errors.append('RA,dec = (%f,%f) -- more than one lenses found at these coordinates!' % (ra,dec))
        else:
            lenses[i]["lens"] = qset[0]
    

    if len(errors) == 0:
        paper["owner"] = user
        paper["access_level"] = "PUB"
        paper_obj = papers_ref.objects.create(**paper)
                
        for j in range(0,len(lenses)):
            paper_obj.lenses_in_paper.add(lenses[j]['lens'],through_defaults=lenses[j]['flags'])
                
        ad_col = ad_col_ref.objects.create(item_type="Paper",myitems=[paper_obj])
        action.send(user,target=users_ref.getAdmin().first(),verb='AddHome',level='success',action_object=ad_col)
    else:
        # Email user with error
        subject = 'SLED: Error while uploading papers'
        from_email = 'sled-no-reply@sled.amnh.org'
        html_message = get_template('emails/error_uploading_papers.html')
        mycontext = {
            'first_name': user.first_name,
            'errors': errors
        }
        html_message = html_message.render(mycontext)
        plain_message = strip_tags(html_message)
        recipient_email = user.email
        send_mail(subject,plain_message,from_email,[recipient_email],html_message=html_message)
        #raise ValidationError(f"Failed to process uploaded paper: {serializer.errors}")

    


    




app.conf.beat_schedule = {
    #'run-every-10-seconds': {
    #    'task': 'mysite.celery.my_periodic_task', # Path to your task
    #    'schedule': timedelta(seconds=10),
    #    'args': ('hello', 'world'),
    #},
    'run-every-monday-morning': {
        'task': 'mysite.celery.my_periodic_task',
        'schedule': crontab(hour=7, minute=30, day_of_week=1), # Every Monday at 7:30 AM
        'args': ('monday', 'special'),
    },
}

    
    
