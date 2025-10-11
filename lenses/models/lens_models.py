# Standard library
import base64
import csv
import inspect
import os
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from random import randint
from urllib.parse import urlparse

# Third-party packages
import simplejson as json
from actstream import action
from bootstrap_modal_forms.generic import (
    BSModalCreateView,
    BSModalDeleteView,
    BSModalFormView,
    BSModalReadView,
    BSModalUpdateView,
)
from bootstrap_modal_forms.mixins import is_ajax
from coolest.template import info as coolest_info
from dirtyfields import DirtyFieldsMixin
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import (
    assign_perm,
    get_groups_with_perms,
    get_objects_for_group,
    get_objects_for_user,
    get_users_with_perms,
    remove_perm,
)
from notifications.signals import notify

# Django core
from django.conf import settings
from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from mysite.language_check import validate_language
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.db import transaction
from multiselectfield import MultiSelectField

from django.views.generic import (
    DetailView,
    ListView,
    TemplateView,
)
from django.views.generic.edit import (
    CreateView,
    DeleteView,
    UpdateView,
)

# Local app imports
from . import AdminCollection, Lenses, SingleObject
 
#from lenses.query_utils import get_combined_qset

# Matplotlib tools
from mysite.celery import celery_save_lens_model
from sled_lens_models.utils import extract_coolest_info_2


def get_mass_choices():
    coolest_names = coolest_info.all_supported_choices['mass_profiles']
    return zip(coolest_names,coolest_names) # Must return list of tuples to use in CharField.Choices

def get_light_choices():
    coolest_names = coolest_info.all_supported_choices['light_profiles']
    return zip(coolest_names,coolest_names) # Must return list of tuples to use in CharField.Choices


class LensModels(SingleObject,DirtyFieldsMixin):
    """
    Describes lens models in a one to many relationship.
    Attributes:
        name (`str`): A name for the lens model.
        description (`text`): What this model is supposed to contain and what's its use.
        lens - Uses a foreign key to the lens associated with each model
        
    """


    name = models.CharField(max_length=30,
                            help_text="A name for your lens model.",
                            unique=True,
                            validators=[validate_language],
                            )
    
    lens = models.ForeignKey(Lenses,
                             null=True,
                             on_delete=models.SET_NULL,
                             related_name='lens_models'
                             )
    
    description = models.TextField(blank=True,
                                   null=True,
                                   default='',
                                   help_text="Description of any important aspects of the model.",
                                   validators=[validate_language],
                                   )
    
    coolest_file = models.FileField(upload_to='lens_models/', blank=True, null=True)
    
    lens_mass_model = MultiSelectField(max_length=40,
                                       blank=True,
                                       null=True,
                                       verbose_name="Lens Mass Models",
                                       help_text="The type of mass profiles that appear in the model.",
                                       choices=get_mass_choices()
                                       )
    
    lens_light_model = MultiSelectField(max_length=40,
                                        blank=True,
                                        null=True,
                                        verbose_name="Lens Light Models",
                                        help_text="The type of lens light profiles that appear in the model.",
                                        choices=get_light_choices()
                                        )
    
    source_light_model = MultiSelectField(max_length=40,
                                          blank=True,
                                          null=True,
                                          verbose_name="Source Light Models",
                                          help_text="The type of source light profiles that appear in the model.",
                                          choices=get_light_choices()
                                          )

    r_eff_source = models.FloatField(blank=True, null=True)

    einstein_radius = models.FloatField(blank=True, null=True)



    class Meta():
        ordering = ["created_at"]
        db_table = "lensmodels"
        verbose_name = "Lens Model"
        verbose_name_plural = "Lens Models"
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('sled_lens_models:lens-model-detail',kwargs={'pk':self.id})

    def dmr_plot_exists(self):
        fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_dmr_plot.png"        
        return default_storage.exists(fname)
    
    def corner_plot_exists(self):
        fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_corner_plot.png"
        return default_storage.exists(fname)
    
    def get_dmr_plot_url(self):
        fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_dmr_plot.png"
        url = default_storage.get_file_url(fname)
        return url

    def get_corner_plot_url(self):
        fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_corner_plot.png"
        url = default_storage.get_file_url(fname)
        return url

    def save(self,*args,**kwargs):
        if self._state.adding:
            super(LensModels,self).save(*args, **kwargs)

            png_dir_name = self.coolest_file.field.upload_to + str(self.pk) + "_pngs"
            default_storage.create_dir(png_dir_name)
            
            if self.access_level == "PUB":
                action.send(self.owner,target=self.lens,verb='AddedTargetLog',level='success',action_object=self)
                notify.send(sender=self.owner,
                            recipient=self.lens.owner,
                            verb='AddedLensModelOwnerNote',
                            level='warning',
                            timestamp=timezone.now(),
                            action_object=self)

        else:
            # Updating object
            dirty = self.get_dirty_fields(verbose=True,check_relationship=True)
            dirty.pop("owner",None) # Do not report ownership changes

            ref_name = self.name
            if "access_level" in dirty.keys():
                # Report only when making public
                if dirty["access_level"]["saved"] == "PRI" and dirty["access_level"]["current"] == "PUB":
                    action.send(self.owner,target=self.lens,verb='MadePublicTargetLog',level='success',object_name=ref_name)
                if dirty["access_level"]["saved"] == "PUB" and dirty["access_level"]["current"] == "PRI":
                    action.send(self.owner,target=self.lens,verb='MadePrivateTargetLog',level='error',object_name=ref_name)
                dirty.pop("access_level",None) # remove from any subsequent report

            if len(dirty) > 0 and self.access_level == "PUB":
                action.send(self.owner,target=self.lens,verb='UpdateTargetLog',level='info',object_name=ref_name,fields=json.dumps(dirty,default=str))

            super(LensModels, self).save(*args, **kwargs)
       
 
        extension = ".tar.gz"
        file_name = f"{self.pk}{extension}"
        fname = self.coolest_file.name
        sled_fname = os.path.join(self.coolest_file.field.upload_to,file_name)
        
        if fname != sled_fname:
            default_storage.copy(fname,sled_fname) #copies the copy from one name to the other #copy fname to sled_fname
            self.coolest_file.name = sled_fname #changes file name of field to proper file name (just the file name)

            ### Make plots
            #png_dir_path = self.coolest_file.path
            #tar_path = settings.MEDIA_ROOT + "/" + self.coolest_file.name
            tar_path = self.coolest_file.name

            transaction.on_commit(lambda: celery_save_lens_model.delay(self.id,tar_path))
            
            '''
            try:                
                with default_storage.read_tar(tar_path) as tar:
                    r_eff_source,einstein_radius,masses,lights,source,free_pars,buf_dmr,buf_corner = extract_coolest_info_2(tar)

                self.lens_mass_model = masses
                self.lens_light_model = lights
                self.source_light_model = source
                self.r_eff_source = r_eff_source
                self.einstein_radius = einstein_radius
                dmr_fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_dmr_plot.png"
                corner_fname = self.coolest_file.field.upload_to + str(self.id) + "_pngs/" + str(self.id) + "_corner_plot.png"
                default_storage.put_object(buf_dmr.read(),dmr_fname)                
                default_storage.put_object(buf_corner.read(),corner_fname)
                    
            except Exception as e:
                raise ValidationError(f"Failed to process COOLEST file: {e}")
            '''
            
            super(LensModels,self).save(*args,**kwargs) #save the changes
            default_storage.mydelete(fname) #delete the original named file

        
        
        

    
# Assign view permission to the owner of a new model
@receiver(post_save,sender=LensModels)
def handle_new_lens_model(sender,**kwargs):
    created = kwargs.get('created')
    if created: # a new lens model was added
        lens_model = kwargs.get('instance')
        perm = 'view_'+lens_model._meta.model_name
        assign_perm(perm,lens_model.owner,lens_model) # lens_model here is not a list, so giving permission ot the user is guaranteed 
