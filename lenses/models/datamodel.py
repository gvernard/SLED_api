from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q, F, CheckConstraint
import abc

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

    class Meta():
        ordering = ["name"]
        db_table = "instruments"
        verbose_name = "instrument"
        verbose_name_plural = "instruments"


class Band(models.Model):
    name = models.CharField(blank=False,
                            unique=True,
                            max_length=100,
                            help_text="A name for the band.")
    info = models.TextField(blank=True,
                            default='',
                            help_text="Any important note about the band.")

    class Meta():
        ordering = ["name"]
        db_table = "bands"
        verbose_name = "band"
        verbose_name_plural = "bands"

    
class DataBase(models.Model):
    lens = models.ForeignKey(Lenses,on_delete=models.CASCADE,related_name="%(class)s")
    instrument = models.ForeignKey(Instrument,to_field='name',on_delete=models.CASCADE)
    date_taken = models.DateField()
    future = models.BooleanField(default=False,
                                 blank=True,
                                 verbose_name="Future",
                                 help_text="Set to true if this is related to an observation scheduled in the future. Then the date_taken field becomes a future date.")
    info = models.TextField(blank=True,
                            default='',
                            help_text="Description of any important aspects of the observation.")

    class Meta():
        abstract = True

        
class Imaging(SingleObject,DataBase):
    exposure_time = models.DecimalField(blank=False,
                                        null=False,
                                        max_digits=7,
                                        decimal_places=3,
                                        verbose_name="Exposure time",
                                        help_text="The exposure time of the image.",
                                        validators=[MinValueValidator(0.0,"Exposure time must be positive."),])
    pixel_size = models.DecimalField(blank=False,
                                     null=False,
                                     max_digits=7,
                                     decimal_places=3,
                                     verbose_name="Pixel size",
                                     help_text="The pixel size of the image.",
                                     validators=[MinValueValidator(0.0,"Pixel size must be positive."),])
    # Field-of-view probably needs to be stored as a rectangular in ra,dec space (Polygon? GeoDjango type?)
    band = models.ForeignKey(Band,to_field='name',on_delete=models.CASCADE)
    image = models.ImageField(upload_to='data/imaging')

    class Meta():
        constraints = [
            CheckConstraint(check=Q(exposure_time__gt=0),name='imaging_exp_time'),
            CheckConstraint(check=Q(pixel_size__gt=0),name='pix_size'),
        ]


class Spectrum(SingleObject,DataBase):
    lambda_min = models.DecimalField(blank=False,
                                     null=False,
                                     max_digits=7,
                                     decimal_places=3,
                                     verbose_name="Minimum wavelength",
                                     help_text="The minimum wavelength of the spectrum.",
                                     validators=[MinValueValidator(0.0,"Minimum wavelength must be positive."),])
    lambda_max = models.DecimalField(blank=False,
                                     null=False,
                                     max_digits=7,
                                     decimal_places=3,
                                     verbose_name="Maximum wavelength",
                                     help_text="The maximum wavelength of the spectrum.",
                                     validators=[MinValueValidator(0.0,"Maximum wavelength must be positive."),])
    exposure_time = models.DecimalField(blank=False,
                                        null=False,
                                        max_digits=7,
                                        decimal_places=3,
                                        verbose_name="Exposure time",
                                        help_text="The exposure time of the image.",
                                        validators=[MinValueValidator(0.0,"Exposure time must be positive."),])
    resolution = models.DecimalField(blank=False,
                                     null=False,
                                     max_digits=7,
                                     decimal_places=3,
                                     verbose_name="Resolution",
                                     help_text="The resolution of the spectrum.",
                                     validators=[MinValueValidator(0.0,"Resolution must be positive."),])
    image = models.ImageField(upload_to='data/imaging')

    class Meta():
        constraints = [
            CheckConstraint(check=Q(exposure_time__gt=0),name='spectrum_exp_time'),
            CheckConstraint(check=Q(lambda_min__lt=F("lambda_max")),name='wavelength_range'),
        ]


class Catalogue(SingleObject,DataBase):
    mag = models.DecimalField(blank=False,
                              null=False,
                              max_digits=7,
                              decimal_places=3,
                              verbose_name="Magnitude",
                              help_text="The magnitude from some catalogue.")
    Dmag = models.DecimalField(blank=False,
                              null=False,
                              max_digits=7,
                              decimal_places=3,
                              verbose_name="Delta magnitude",
                              help_text="Uncertainty on the magnitude.")
    distance = models.DecimalField(blank=False,
                                   null=False,
                                   max_digits=7,
                                   decimal_places=3,
                                   verbose_name="Distance",
                                   help_text="Distance from the RA,dec of the lens in arcsec.",
                                   validators=[MinValueValidator(0.0,"Distance must be positive."),])
    band = models.ForeignKey(Band,to_field='name',on_delete=models.CASCADE)

    class Meta():
        constraints = [
            CheckConstraint(check=Q(distance__gt=0),name='distance'),
        ]
