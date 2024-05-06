from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q,F,Count,CharField,CheckConstraint
from django.apps import apps

from mysite.language_check import validate_language


class TimeLineManager(models.Manager):
    def current(self):
        now = timezone.now()
        qset = super().get_queryset().filter(from_date__lt=now,to_date__gt=now)
        return qset

    def future(self):
        now = timezone.now()
        qset = super().get_queryset().filter(from_date__gt=now)
        return qset

    def past(self):
        now = timezone.now()
        qset = super().get_queryset().filter(to_date__lt=now)
        return qset


class PersistentMessage(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    from_date = models.DateTimeField(blank=False,
                                     help_text="The date to start displaying the message.")
    to_date = models.DateTimeField(blank=False,
                                   help_text="The date to end displaying the message.")
    tagChoices = (
        ("info",'info'),
        ("success",'success'),
        ("warning",'warning'),
        ("danger",'danger')
    )
    tag = models.CharField(max_length=100,
                           blank=False,
                           choices=tagChoices)
    message = models.TextField(blank=False,
                               default='',
                               help_text="The content of the message.",
                               validators=[validate_language],
                               )

    timeline = TimeLineManager()
    objects = models.Manager()
    
    class Meta():
        get_latest_by = ["modified_at","created_at"]
        constraints = [
            CheckConstraint(check=Q(modified_at__gt=F('created_at')),name='%(class)s_modified_after_created'),
            CheckConstraint(check=Q(from_date__lt=F('to_date')),name='%(class)s_to_after_from')
        ]
