from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.apps import apps
from django.urls import reverse
from django.db.models import F

from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import assign_perm,remove_perm
from gm2m import GM2MField
import simplejson as json
from actstream import action
from dirtyfields import DirtyFieldsMixin

import inspect
from itertools import groupby
from operator import itemgetter

from . import SingleObject, AdminCollection, Lenses
from mysite.language_check import validate_language


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
    description = models.CharField(max_length=250,
                                   null=True,
                                   blank=True,
                                   help_text="A description for your lens model.",
                                   validators=[validate_language],
                                   )
    category = models.CharField(max_length=100,
                                verbose_name="Category",
                                help_text="Lens Model Category Type.",
                                validators=[validate_language])

    lens = models.ForeignKey(Lenses,
                             null=True,
                             on_delete=models.SET_NULL,
                             related_name='lens_models')
    
    info = models.TextField(blank=True,
                            null=True,
                            default='',
                            help_text="Description of any important aspects of the model.",
                            validators=[validate_language],
                            )
    
    file = models.FileField(upload_to='lens_model_files/', blank=True, null=True)


    class Meta():
        ordering = ["created_at"]
        db_table = "lensmodels"
        verbose_name = "Lens Model"
        verbose_name_plural = "Lens Models"
    
    def __str__(self):
        return self.name
    #defines how object appears when converted to a string 

    def get_absolute_url(self):
        return reverse('sled_lens_models:lens-model-detail',kwargs={'pk':self.id})
    #this does not exist yet(must code) - calls lens model detail view
    #(?) first partis app and second part is view
    


