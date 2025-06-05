from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.apps import apps
from django.urls import reverse
from django.db.models import F

from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import assign_perm,remove_perm
import simplejson as json
from actstream import action
from dirtyfields import DirtyFieldsMixin

import inspect
from itertools import groupby
from operator import itemgetter

from . import SingleObject, AdminCollection, Lenses
from mysite.language_check import validate_language


class LensModel(SingleObject, DirtyFieldsMixin):
    lens = models.ForeignKey(Lenses,
                             null=True,
                             on_delete=models.SET_NULL,
                             related_name="%(class)s")
    name = models.CharField(max_length=30,
                            help_text="A name for your collection.",
                            unique=True,
                            validators=[validate_language],
                            )
    description = models.CharField(max_length=250,
                                   null=True,
                                   blank=True,
                                   help_text="A description for your collection.",
                                   validators=[validate_language],
                                   )

    class Meta(SingleObject.Meta):
        db_table = "lens_models"
        verbose_name = "Lens Model"
        verbose_name_plural = "Lens Models"
        ordering = ["modified_at"]
        # Constrain the number of objects in a collection?

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return 'dummy'
