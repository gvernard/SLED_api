from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q, F, CheckConstraint
from django.conf import settings
from django.utils import timezone
from multiselectfield import MultiSelectField
from dirtyfields import DirtyFieldsMixin
from actstream import action
from notifications.signals import notify
import os
import simplejson as json
from pprint import pprint

from . import SingleObject, Lenses


class Instrument(models.Model):
    name = models.CharField(blank=False,
                            unique=True,
                            max_length=100,
                            help_text="A name for the instrument.")
    extended_name = models.CharField(blank=False,
                            max_length=100,
                            help_text="The extended name for the instrument.")    
    info = models.TextField(blank=True,
                            default='',
                            help_text="Any important note about the instrument.")

    BaseTypeChoices = (
        ('Spectrum','Spectrum'),
        ('Imaging','Imaging'),
        ('Catalogue','Catalogue'),
    )
    base_types = MultiSelectField(max_length=100,
                                  blank=True,
                                  null=True,
                                  choices=BaseTypeChoices)

    class Meta():
        ordering = ["name"]
        db_table = "instruments"
        verbose_name = "Instrument"
        verbose_name_plural = "Instruments"

    def __str__(self):
        return self.name

    
class Band(models.Model):
    name = models.CharField(blank=False,
                            unique=True,
                            max_length=100,
                            help_text="A name for the band.")
    info = models.TextField(blank=True,
                            default='',
                            help_text="Any important note about the band.")

    wavelength = models.FloatField(blank=False,
                                   default=0,
                                   help_text="Central wavelength of the band [nm].",
                                   validators=[MinValueValidator(0.0,"Central wavelength must be positive."),])

    class Meta():
        ordering = ["wavelength"]
        db_table = "bands"
        verbose_name = "Band"
        verbose_name_plural = "Bands"

    def __str__(self):
        return self.name

    
class DataBase(models.Model):
    lens = models.ForeignKey(Lenses,
                             on_delete=models.CASCADE,
                             related_name="%(class)s")
    instrument = models.ForeignKey(Instrument,
                                   verbose_name="Instrument",
                                   to_field='name',
                                   on_delete=models.PROTECT)
    date_taken = models.DateField(blank=False,
                                  verbose_name="Date taken",
                                  help_text="The date when the data were taken (can be in the future).")
    exists = models.BooleanField(default=True,
                                 blank=True, 
                                 verbose_name="Exists flag",
                                 help_text="This field is a flag to help with bookkeeping of which objects have been checked for which data.")
    future = models.BooleanField(default=False,
                                 blank=True,
                                 verbose_name="Future",
                                 help_text="Set to true if this is related to an observation scheduled in the future. Then the date_taken field becomes a future date.")
    info = models.TextField(blank=True,
                            null=True,
                            default='',
                            help_text="Description of any important aspects of the observation.")

    class Meta():
        abstract = True


        
        
class Imaging(SingleObject,DataBase,DirtyFieldsMixin):
    exposure_time = models.DecimalField(blank=True,
                                        null=True,
                                        max_digits=12,
                                        decimal_places=3,
                                        verbose_name="Exposure time",
                                        help_text="The exposure time of the image [seconds].",
                                        validators=[MinValueValidator(0.0,"Exposure time must be positive."),])
    pixel_size = models.DecimalField(blank=True,
                                     null=True,
                                     max_digits=7,
                                     decimal_places=3,
                                     verbose_name="Pixel size",
                                     help_text="The pixel size of the image [arcsec].",
                                     validators=[MinValueValidator(0.0,"Pixel size must be positive."),])
    # Field-of-view probably needs to be stored as a rectangular in ra,dec space (Polygon? GeoDjango type?)
    band = models.ForeignKey(Band,
                             to_field='name',
                             verbose_name="Band",
                             on_delete=models.PROTECT)
    image = models.ImageField(blank=True,
                              upload_to='imaging')
    url = models.URLField(blank=True,
                          max_length=300)

    FIELDS_TO_CHECK = ['instrument','band','exposure_time','pixel_size','image','date_taken','info','future']
    
    class Meta():
        constraints = [
            CheckConstraint(check=Q(exposure_time__gt=0),name='imaging_exp_time'),
            CheckConstraint(check=Q(pixel_size__gt=0),name='pix_size'),
        ]
        ordering = ["created_at"]
        db_table = "imaging"
        verbose_name = "Imaging data entry"
        verbose_name_plural = "Imaging data entries"


    def __str__(self):
        return self.lens.name + " - " + self.instrument.name + " " + self.band.name

    
    def get_absolute_url(self):
        return self.lens.get_absolute_url()

    
    def save(self,*args,**kwargs):
        if self._state.adding and self.access_level == "PUB":
            # Creating object for the first time, calling save first to create a primary key
            super(Imaging,self).save(*args,**kwargs)
            if self.exists:
                action.send(self.owner,target=self.lens,verb='AddedTargetLog',level='success',action_object=self)
                notify.send(sender=self.owner,
                            recipient=self.lens.owner,
                            verb='AddedDataOwnerNote',
                            level='warning',
                            timestamp=timezone.now(),
                            action_object=self)
        else:
            # Updating object
            dirty = self.get_dirty_fields(verbose=True,check_relationship=True)
            dirty.pop("owner",None) # Do not report ownership changes

            if "access_level" in dirty.keys():
                # Report only when making public
                if dirty["access_level"]["saved"] == "PRI" and dirty["access_level"]["current"] == "PUB":
                    action.send(self.owner,target=self.lens,verb='MadePublicTargetLog',level='warning',action_object=self)
                dirty.pop("access_level",None) # remove from any subsequent report

            if "image" in dirty.keys():
                action.send(self.owner,target=self.lens,verb='ImageChangeTargetLog',level='info',action_object=self)
                dirty.pop("image",None) # remove from any subsequent report
                
            if len(dirty) > 0 and self.access_level == "PUB":
                action.send(self.owner,target=self.lens,verb='UpdateTargetLog',level='info',action_object=self,fields=json.dumps(dirty,default=str))
            
        if self.exists:
            # Create new file and remove old one        
            super(Imaging,self).save(*args,**kwargs)
            fname = '/'+self.image.name
            if not os.path.exists(settings.MEDIA_ROOT+'/imaging/'):
                os.mkdir(settings.MEDIA_ROOT+'/imaging/')
            sled_fname = '/imaging/' + str( self.pk ) + '.png'
            if fname != sled_fname:
                os.rename(settings.MEDIA_ROOT+fname,settings.MEDIA_ROOT+sled_fname)
                self.image.name = sled_fname

        super(Imaging,self).save(*args,**kwargs)

            
        
class Spectrum(SingleObject,DataBase,DirtyFieldsMixin):
    lambda_min = models.DecimalField(blank=True,
                                     null=True,
                                     max_digits=10,
                                     decimal_places=3,
                                     verbose_name="&lambda;<sub>min</sub>",
                                     help_text="The minimum wavelength of the spectrum [nm].",
                                     validators=[MinValueValidator(0.0,"Minimum wavelength must be positive."),])
    lambda_max = models.DecimalField(blank=True,
                                     null=True,
                                     max_digits=10,
                                     decimal_places=3,
                                     verbose_name="&lambda;<sub>max</sub>",
                                     help_text="The maximum wavelength of the spectrum [nm].",
                                     validators=[MinValueValidator(0.0,"Maximum wavelength must be positive."),])
    exposure_time = models.DecimalField(blank=True,
                                        null=True,
                                        max_digits=10,
                                        decimal_places=3,
                                        verbose_name="Exposure time",
                                        help_text="The exposure time of the image [seconds].",
                                        validators=[MinValueValidator(0.0,"Exposure time must be positive."),])
    resolution = models.DecimalField(blank=True,
                                     null=True,
                                     max_digits=10,
                                     decimal_places=3,
                                     verbose_name="Resolution",
                                     help_text="The resolution of the spectrum [nm].",
                                     validators=[MinValueValidator(0.0,"Resolution must be positive."),])
    image = models.ImageField(blank=True,
                              upload_to='data/spectrum')

    FIELDS_TO_CHECK = ['instrument','exposure_time','resolution','lambda_min','lambda_max','image','date_taken','info','future']

    class Meta():
        constraints = [
            CheckConstraint(check=Q(exposure_time__gt=0),name='spectrum_exp_time'),
            CheckConstraint(check=Q(lambda_min__lt=F("lambda_max")),name='wavelength_range'),
        ]
        ordering = ["created_at"]
        db_table = "spectrum"
        verbose_name = "Spectrum"
        verbose_name_plural = "Spectra"

        
    def __str__(self):
        return self.lens.name + " - " + self.instrument.name

    
    def get_absolute_url(self):
        return self.lens.get_absolute_url()

    
    def save(self,*args,**kwargs):
        if self._state.adding:
            if self.exists and self.access_level == "PUB":
                # Creating object for the first time, calling save first to create a primary key
                super(Spectrum,self).save(*args,**kwargs)
                action.send(self.owner,target=self.lens,verb='AddedTargetLog',level='success',action_object=self)
        else:
            # Updating object
            dirty = self.get_dirty_fields(verbose=True,check_relationship=True)
            dirty.pop("owner",None) # Do not report ownership changes
            
            if "access_level" in dirty.keys():
                # Report only when making public
                if dirty["access_level"]["saved"] == "PRI" and dirty["access_level"]["current"] == "PUB":
                    action.send(self.owner,target=self.lens,verb='MadePublicTargetLog',level='warning',action_object=self)
                dirty.pop("access_level",None) # remove from any subsequent report

            if "image" in dirty.keys():
                action.send(self.owner,target=self.lens,verb='ImageChangeTargetLog',level='info',action_object=self)
                dirty.pop("image",None) # remove from any subsequent report
                
            if len(dirty) > 0 and self.access_level == "PUB":
                action.send(self.owner,target=self.lens,verb='UpdateTargetLog',level='info',action_object=self,fields=json.dumps(dirty,default=str))

        if self.exists:
            # Create new file and remove old one
            super(Spectrum,self).save(*args,**kwargs)
            fname = '/'+self.image.name
            if not os.path.exists(settings.MEDIA_ROOT+'/spectrum/'):
                os.mkdir(settings.MEDIA_ROOT+'/spectrum/')
            sled_fname = '/spectrum/' + str( self.pk ) + '.png'
            if fname != sled_fname:
                os.rename(settings.MEDIA_ROOT+fname,settings.MEDIA_ROOT+sled_fname)
                self.image.name = sled_fname

        super(Spectrum,self).save(*args,**kwargs)


    
class Catalogue(SingleObject,DataBase,DirtyFieldsMixin):
    radet = models.DecimalField(blank=True,
                              null=True,
                              max_digits=10,
                              decimal_places=7,
                              verbose_name="RA",
                              help_text="Right ascension of detection [degrees]")
    decdet = models.DecimalField(blank=True,
                              null=True,
                              max_digits=10,
                              decimal_places=7,
                              verbose_name="DEC",
                              help_text="Declination of detection [degrees]")
    mag = models.DecimalField(blank=True,
                              null=True,
                              default=None,
                              max_digits=10,
                              decimal_places=3,
                              verbose_name="Mag",
                              help_text="The magnitude from some catalogue.")
    Dmag = models.DecimalField(blank=True,
                              null=True,
                              default=None,
                              max_digits=7,
                              decimal_places=3,
                              verbose_name="&Delta; Mag",
                              help_text="Uncertainty on the magnitude.")
    distance = models.DecimalField(blank=True,
                                   null=True,
                                   max_digits=7,
                                   decimal_places=3,
                                   verbose_name="Distance",
                                   help_text="Distance from the RA,dec of the lens [arcsec].",
                                   validators=[MinValueValidator(0.0,"Distance must be positive."),])
    band = models.ForeignKey(Band,
                             to_field='name',
                             verbose_name="Band",
                             on_delete=models.PROTECT)

    FIELDS_TO_CHECK = ['instrument','band','radet','decdet','mag','Dmag','distance','date_taken','info','future']
        
    class Meta():
        constraints = [
            CheckConstraint(check=Q(distance__gt=0),name='distance'),
            CheckConstraint(check=Q(radet__range=(0,360)),name='radet_range'),
            CheckConstraint(check=Q(decdet__range=(-90,90)),name='decdet_range'),
        ]
        ordering = ["created_at"]
        db_table = "catalogue"
        verbose_name = "Catalogue data entry"
        verbose_name_plural = "Catalogue data entries"

        
    def __str__(self):
        return self.lens.name + " - " + self.instrument.name + " - " + self.band.name

    
    def get_absolute_url(self):
        return self.lens.get_absolute_url()

    
    def save(self,*args,**kwargs):
        if self._state.adding and self.access_level == "PUB":
            # Creating object for the first time, calling save first to create a primary key
            super(Catalogue,self).save(*args,**kwargs)
            if self.exists:
                action.send(self.owner,target=self.lens,verb='AddedTargetLog',level='success',action_object=self)
        else:
            # Updating object
            dirty = self.get_dirty_fields(verbose=True,check_relationship=True)
            dirty.pop("owner",None) # Do not report ownership changes
            
            if "access_level" in dirty.keys():
                # Report only when making public
                if dirty["access_level"]["saved"] == "PRI" and dirty["access_level"]["current"] == "PUB":
                    action.send(self.owner,target=self.lens,verb='MadePublicTargetLog',level='warning',action_object=self)
                dirty.pop("access_level",None) # remove from any subsequent report
                    
            if len(dirty) > 0 and self.access_level == "PUB":
                action.send(self.owner,target=self.lens,verb='UpdateTargetLog',level='info',action_object=self,fields=json.dumps(dirty,default=str))
                
        super(Catalogue,self).save(*args,**kwargs)
