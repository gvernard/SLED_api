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

from . import SingleObject, AdminCollection
from mysite.language_check import validate_language


class Lens_Models(SingleObject):
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
    lens = models.ForeignKey(Lenses,
                             null=True,
                             on_delete=models.SET_NULL,
                             related_name="%(class)s")

    class Meta():
        ordering = ["name"]
        db_table = "lensmodels"
        verbose_name = "Lens Model"
        verbose_name_plural = "Lens Models"
    
    def __str__(self):
        return self.name
    #defines how object appears when converted to a string 

    def get_absolute_url(self):
        return reverse('sled_lens_models:lens-models-detail',kwargs={'pk':self.id})
    #this does not exist yet(must code) - calls lens model detail view
    #(?) first partis app and second part is view
    


