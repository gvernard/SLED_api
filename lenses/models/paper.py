from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.apps import apps
from django.urls import reverse
from django.db.models import Q, CheckConstraint, UniqueConstraint

from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import assign_perm
from gm2m import GM2MField
import simplejson as json
from actstream import action
from dirtyfields import DirtyFieldsMixin

import inspect
from itertools import groupby
from operator import itemgetter

from . import SingleObject, Lenses, Users


class Paper(SingleObject):
    """
    Describes a paper.
    It relates to lenses through a many-to-many relationship, which does not need to be a generic one.
    The relation between papers and lenses should be many-to-many, but between papers and models or scores it should be one-to-many.
    The latter would be created by models and scores not by papers, i.e. a model would require a preexisting paper.

    Attributes:
        bibcode (`str`): The bibcode of the paper.
        year (`int`): The year the paper was published (filled automatically by calling the ADS API).
        first_author (`text`): The first author of the paper (filled automatically by calling the ADS API).
        title (`text`): The title of the paper (filled automatically by calling the ADS API).
        cite_as (`text`): e.g. "Vernardos and Koopmans (2022)", or "Lemon et al. (2022)" (filled automatically by calling the ADS API).
        lenses_in_paper (`Lenses`): A many-to-many field with an intermediate model.
    """
    ads_id = models.IntegerField(unique=True,
                                 null=True,
                                 help_text="Unique identifier from the ADS database.")
    bibcode = models.CharField(max_length=19,
                               unique=True,
                               help_text="The paper's bibcode (not unique, the same 'work'/paper can have several bibcodes).")
    year = models.IntegerField(help_text="The year the paper was published.")
    first_author = models.CharField(max_length=100,
                                    blank=False,
                                    null=True,
                                    help_text="The name of the first author."
                                    )
    title = models.CharField(max_length=300,
                             blank=False,
                             null=True,
                             help_text="The title of the paper."
                             )
    cite_as = models.CharField(max_length=200,
                               blank=False,
                               null=True,
                               help_text="For example: Vernardos and Lemon (2022), or Vernardos et al. (2022)."
                               )
    lenses_in_paper = models.ManyToManyField(
        Lenses,
        related_name='papers',
        through='PaperLensConnection',
        through_fields=('paper','lens'),
        help_text="A many-to-many relationship between Paper and Lenses."
    )

    class Meta():
        db_table = "papers"
        verbose_name = "paper"
        verbose_name_plural = "papers"
        ordering = ["year","first_author"]
        # constrain the number of lenses per paper?
        
    def __str__(self):
        return '%s' % (self.cite_as)

    def save(self,*args,**kwargs):
        ad_col = AdminCollection.objects.create(item_type="Paper",myitems=[self])
        action.send(self.owner,target=Users.getAdmin().first(),verb='AddHome',level='success',action_object=ad_col)
        for lens in self.lenses_in_paper:
            action.send(self.owner,target=lens,verb='AddPaperTargetLog',level='success',action_object=self)
        super(Paper,self).save(*args,**kwargs)
    
    def get_absolute_url(self):
        return reverse('sled_papers:paper-detail',kwargs={'pk':self.id})

    def get_ads_url(self):
        return "https://ui.adsabs.harvard.edu/abs/" + self.bibcode
   
    
class PaperLensConnection(models.Model):
    paper = models.ForeignKey(Paper,on_delete=models.CASCADE)
    lens = models.ForeignKey(Lenses,on_delete=models.CASCADE)
    discovery = models.BooleanField(help_text="A flag for a discovery paper. Must be unique per lens.")
    classification = models.BooleanField(help_text="A flag for a classication paper.")
    model = models.BooleanField(help_text="A flag for a modelling paper.")
    redshift = models.BooleanField(help_text="A flag for a paper measuring the redshift.")

    #class Meta():
    #    constraints = [
    #        UniqueConstraint(fields=['lens'],condition=Q(discovery=True),name='unique_discovery')
    #    ]
