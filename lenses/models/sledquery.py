from django.db import models
from django.apps import apps
from django.utils import timezone
from django.dispatch import receiver
from django.urls import reverse

import urllib

from . import SingleObject


class SledQuery(SingleObject):
    name = models.CharField(max_length=30,
                            help_text="A name for your query")
    description = models.CharField(max_length=200,
                                   null=True,
                                   blank=True,
                                   help_text="A description for your query"
                                   )
    cargo = models.JSONField(help_text="A json object holding the non-empty, non-false query fields.")

    class Meta(SingleObject.Meta):
        db_table = "sled_query"
        verbose_name = "sled_query"
        verbose_name_plural = "sled_queries"
        ordering = ["created_at"]
        
    def __str__(self):
        return self.name

    def get_GET_url(self):
        url = reverse('lenses:lens-query') + '?' + urllib.parse.urlencode(self.cargo)
        return url
    
    def compress_to_cargo(self,form_dict):
        cargo = {}
        for key,val in form_dict.items():
            if val not in [None, False, '', []]:
                cargo[key] = val
        return cargo
