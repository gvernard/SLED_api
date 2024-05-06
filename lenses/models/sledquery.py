from django.db import models
from django.apps import apps
from django.utils import timezone
from django.dispatch import receiver
from django.urls import reverse

import urllib

from . import SingleObject
from mysite.language_check import validate_language


class SledQuery(SingleObject):
    name = models.CharField(max_length=100,
                            help_text="A name for your query",
                            validators=[validate_language])
    description = models.CharField(max_length=200,
                                   null=True,
                                   blank=True,
                                   help_text="A description for your query",
                                   validators=[validate_language]
                                   )
    cargo = models.JSONField(help_text="A json object holding the non-empty, non-false query fields.")

    class Meta(SingleObject.Meta):
        db_table = "sled_query"
        verbose_name = "sled query"
        verbose_name_plural = "sled queries"
        ordering = ["created_at"]
        
    def __str__(self):
        return self.name

    def get_GET_url(self):
        #note the additional True parameter which turns lists into repeated fields
        url = reverse('lenses:lens-query') + '?' + urllib.parse.urlencode(self.cargo, True)
        return url
    
    def compress_to_cargo(self,form_dict):
        cargo = {}
        for key,val in form_dict.items():
            #note that False==0 evaluates True but False is 0 evaluates False
            if True not in [val is bad for bad in [None, False, '', []]]:
                cargo[key] = val
        return cargo
