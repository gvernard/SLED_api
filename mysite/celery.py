from __future__ import absolute_import
import os
import time

from celery import Celery
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.apps import apps

from django.core.files.storage import default_storage
from sled_lens_models.utils import extract_coolest_info_2


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

app = Celery('mysite')
app.config_from_object('django.conf:settings',namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
#app.autodiscover_tasks()


@app.task
def my_divide(x,y):
    import time
    time.sleep(5)
    return x / y


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


    
