from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db.models import Q, F, Func, FloatField, CheckConstraint
from django.urls import reverse
from django.conf import settings
from functools import partial as curry 
from multiselectfield import MultiSelectField

from dirtyfields import DirtyFieldsMixin
from actstream import action
from guardian.shortcuts import get_users_with_perms
from django_resized import ResizedImageField

import os
import math
from astropy import units as u
from astropy.coordinates import SkyCoord
import simplejson as json

from . import SingleObject
from mysite.language_check import validate_language


class ProximateLensManager(models.Manager):
    """
    Attributes:
        check_radius (`float`): A radius in arcsec, representing an area around each existing lens.
    """
    check_radius = 16 # in arcsec

    
    def get_DB_neighbours(self,lens,radius=None,user=None):
        """
        Checks if a lens object *not yet in the database* has any lenses close to it.
        If a user is given, then it checks both for PUB and PRI lenses.
        If no user is given, then it checks only PUB lenses.
        It excludes itself from the returned queryset (relevant if updating the object).

        Args:
            lens (`Lenses`): A lens around which to search.
            radius (`float`): A value for the search radius in arcsec (OPTIONAL)
            user (`User`): A user object (OPTIONAL)
            
        Returns:
            Queryset (`Lenses`): Returns which of the existing lenses in the database are within a 'radius' from the lens.
        """
        if not radius:
            radius = self.check_radius
            
        if not user:
            qset = super().get_queryset().filter(access_level='PUB')
        else:
            qset = Lenses.accessible_objects.all(user)
            
        qset = qset.annotate(distance=Func(F('ra'),F('dec'),lens.ra,lens.dec,function='distance_on_sky',output_field=FloatField())).filter(distance__lt=radius).exclude(id=lens.id)
        return qset


        
    def get_DB_neighbours_many(self,lenses,radius=None,user=None):
        """
        Loops over a list of lenses and calls repeatedly get_DB_neighbours.

        Args:
            lenses [List(`Lenses`)]: A list of Lenses objects.

        Returns:
            index_list (List[int]): A list of indices to the original input list indicating those lenses that have proximate existing lenses. 
            neis_list (List[`Lenses`]): Returns a list of querysets matching the list of lenses from index_list. Each queryset contains the neighbours of each lens.
        """   
        index_list = []
        neis_list = [] # A list of non-empty querysets
        for i,lens in enumerate(lenses):
            neis = self.get_DB_neighbours(lens,radius=radius,user=user)
            if neis:
                index_list.append(i)
                neis_list.append(neis)
        return index_list,neis_list

    
    def get_DB_neighbours_anywhere(self,ra,dec,radius=None,user=None):
        """
        Same as get_DB_neighbours but this time untied to any lens object (from the database or not).
        If a user is given, then it checks both for PUB and PRI lenses.
        If no user is given, then it checks only PUB lenses.

        Args:
            ra (`float`): The RA of any point on the sky.
            dec (`float`): The DEC of any point on the sky.
            radius (`float`): A value for the search radius in arcsec (OPTIONAL)
            user (`User`): A user object (OPTIONAL)

        Returns:
            Queryset (`Lenses`): Returns which of the existing lenses in the database are within a 'radius' from the lens.
        """
        if not radius:
            radius = self.check_radius

        if not user:
            qset = super().get_queryset().filter(access_level='PUB')
        else:
            qset = Lenses.accessible_objects.all(user)
        
        qset = qset.annotate(distance=Func(F('ra'),F('dec'),ra,dec,function='distance_on_sky',output_field=FloatField())).filter(distance__lt=radius)
        return qset


    def get_DB_neighbours_anywhere_many(self,ras,decs,radius=None,user=None):
        """
        Loops over a list of Ra and dec and calls repeatedly get_DB_neighbours_anywhere.

        Args:
            ra [List(`float`)]: A list of RA values.
            dec [List(`float`)]: A list of dec values.
            radius (`float`): A value for the search radius in arcsec (OPTIONAL)
            user (`User`): A user object (OPTIONAL)

        Returns:
            index_list (List[int]): A list of indices to the original input list indicating those lenses that have proximate existing lenses. 
            neis_list (List[`Lenses`]): Returns a list of querysets matching the list of lenses from index_list. Each queryset contains the neighbours of each lens.
        """   
        index_list = []
        neis_list = [] # A list of non-empty querysets
        for i in range(0,len(ras)):
            neis = self.get_DB_neighbours_anywhere(ras[i],decs[i],radius,user)
            if neis:
                index_list.append(i)
                neis_list.append(neis)
        return index_list,neis_list



    def get_DB_neighbours_anywhere_subqset(self,ra,dec,lens_subqset,radius=None):
        """
        Same as get_DB_neighbours_anywhere but this time filters an existing queryset (lens_subqset) that is passed as argument.
        No need for a User object.
        
        Args:
            ra [List(`float`)]: A list of RA values.
            dec [List(`float`)]: A list of dec values.
            lens_subqset (Queryset `Lenses`): A queryset of Lenses.
            radius (`float`): A value for the search radius in arcsec (OPTIONAL)

        Returns:
            Queryset (`Lenses`): Returns a queryset filtered by proximity to the given ra,dec.
        """
        if not radius:
            radius = self.check_radius
            
        qset = lens_subqset.annotate(distance=Func(F('ra'),F('dec'),ra,dec,function='distance_on_sky',output_field=FloatField())).filter(distance__lt=radius)
        return qset





class Lenses(SingleObject,DirtyFieldsMixin):
    ra = models.DecimalField(blank=False,
                             max_digits=10,
                             decimal_places=6,
                             verbose_name="RA",
                             help_text="The RA of the lens [degrees] between 0 and 360.",
                             validators=[MinValueValidator(0.0,"RA must be positive."),
                                         MaxValueValidator(360,"RA must be less than 360 degrees.")])
    dec = models.DecimalField(blank=False,
                              max_digits=10,
                              decimal_places=6,
                              verbose_name="DEC",
                              help_text="The DEC of the lens [degrees] between -90 and 90.",
                              validators=[MinValueValidator(-90,"DEC must be above -90 degrees."),
                                          MaxValueValidator(90,"DEC must be below 90 degrees.")])
    name = models.CharField(unique=False,
                            blank=True,
                            max_length=100,
                            help_text="An identification for the lens, e.g. the usual phone numbers.",
                            #validators=[validate_language],
                            )

    alt_name = models.CharField(max_length=200,
                                blank=True,
                                null=True,
                                help_text="A list of comma-separated strings for the alternative names of the system.",
                                #validators=[validate_language],
                                )

    score = models.DecimalField(blank=True,
                             null=True,
                             max_digits=7,
                             decimal_places=4,
                             verbose_name="Candidate score",
                             help_text="The score of the candidate based on the classification guidelines (between 0 and 3).",
                             validators=[MinValueValidator(0.0,"Score must be positive."),
                                         MaxValueValidator(3.,"Score must be less than or equal to 3.")])

    image_sep = models.DecimalField(blank=True,
                                    null=True,
                                    max_digits=6,
                                    decimal_places=4,
                                    verbose_name="Image separation",
                                    help_text="An estimate of the maximum image separation or arc radius [arcsec]. Must be positive and <100.",
                                    validators=[MinValueValidator(0.0,"Separation must be positive."),
                                                MaxValueValidator(100,"Separation must be less than 10 arcsec.")])

    info = models.TextField(blank=True,
                            default='',
                            help_text="Description of any important aspects of this system, e.g. discovery/interesting features/multiple discoverers/etc.",
                            validators=[validate_language],
                            )
    
    n_img = models.IntegerField(blank=True,
                                null=True,
                                verbose_name="N<sub>images</sub>",
                                help_text="The number of source images, if known. Must be an integer.",
                                validators=[MinValueValidator(2,"For this to be a lens candidate, it must have at least 2 images of the source"),
                                            MaxValueValidator(20,"Wow, that's a lot of images, are you sure?")])
    
    #mugshot = models.ImageField(upload_to='lenses', validators=[FileExtensionValidator(['png','jpeg','jpg'])])
    mugshot = ResizedImageField(upload_to='lenses',
                                force_format='PNG',
                                validators=[FileExtensionValidator(['png','jpeg','jpg'])],
                                help_text="A 'mugshot' image of the lens, usually a pretty picture characteristic of the system."
                                )
    
    FlagChoices = (
        ('CONFIRMED','Confirmed'),
        ('CANDIDATE','Candidate'),
        ('CONTAMINANT','Contaminant'),
    )
    flag = models.CharField(max_length=20,
                            blank=False,
                            null=False,
                            default='CANDIDATE',
                            verbose_name="Flag",
                            help_text="Whether the system is a confirmed lens, a candidate, or a confirmed contaminant.",
                            choices=FlagChoices)
    
    ImageConfChoices = (
        ('LONG-AXIS CUSP','Long-axis Cusp'),
        ('SHORT-AXIS CUSP','Short-axis Cusp'),
        ('NAKED CUSP','Naked Cusp'),
        ('CUSP','Cusp'),
        ('CENTRAL IMAGE','Central Image'),
        ('FOLD','Fold'),
        ('CROSS','Cross'),
        ('DOUBLE','Double'),
        ('QUAD','Quad'),
        ('RING','Ring'),
        ('ARC','Arc')
    )
    image_conf = MultiSelectField(max_length=100,
                                  blank=True,
                                  null=True,
                                  verbose_name="Image configuration",
                                  help_text="The configuration of the lensing system, if known. Multiple choices are possible.",
                                  choices=ImageConfChoices)
    LensTypeChoices = (
        ('GALAXY','Galaxy'),
        ('LTG','Late-type Galaxy'),
        ('SPIRAL','Spiral galaxy'),
        ('GALAXY PAIR','Galaxy pair'),
        ('GROUP','Group of galaxies'),
        ('CLUSTER','Galaxy cluster'),
        ('CLUSTER MEMBER','Galaxy cluster member'),
        ('QUASAR','Quasar'),
        ('LRG','Luminous Red Galaxy'),
        ('ETG', 'Early Type Galaxy'),
        ('ELG', 'Emission Line Galaxy')
    )
    lens_type = MultiSelectField(max_length=100,
                                 blank=True,
                                 null=True,
                                 verbose_name="Lens type",
                                 help_text="The type of the lensing galaxy, if known. Multiple choices are possible.",
                                 choices=LensTypeChoices)
    
    SourceTypeChoices = (
        ('GALAXY','Galaxy'),
        ('ETG','Early-type Galaxy'),
        ('SMG','Sub-millimetre Galaxy'),
        ('QUASAR','Quasar'),
        ('DLA','DLA'),
        ('PDLA','PDLA'),
        ('RADIO-LOUD','Radio-loud'),
        ('BAL QUASAR','BAL Quasar'),
        ('ULIRG','ULIRG'),
        ('BL Lac','BL Lac'),
        ('LOBAL QUASAR','LoBAL Quasar'),
        ('FELOBAL QUASAR','FeLoBAL Quasar'),
        ('EXTREME RED OBJECT','Extreme Red Object'),
        ('RED QUASAR','Red Quasar'),
        ('GW','Gravitational Wave'),
        ('FRB','Fast Radio Burst'),
        ('GRB','Gamma Ray Burst'),
        ('SN','Supernova'),
        ('LBG', 'Lyman Break Galaxy'),
        ('ELG', 'Emission Line Galaxy')
    )

    source_type = MultiSelectField(max_length=100,
                                   blank=True,
                                   null=True,
                                   verbose_name="Source type",
                                   help_text="The type of the source, if known. Multiple choices are possible.",
                                   choices=SourceTypeChoices)

    ContaminantTypeChoices = (
        ('PROJECTED QUASARS', 'Projected quasars'),
        ('DUAL QUASAR', 'Dual quasar'),
        ('QUASAR+STAR', 'Projected quasar + star'),
        ('STAR+STAR', 'Star + star'),
        ('STARS', 'Stars'),
        ('STAR-FORMING GALAXY', 'Star-forming galaxy'),
        ('STARS+GALAXY', 'Stars + galaxy'),
        ('STAR+GALAXY', 'Star + galaxy'),
        ('STAR+OTHER', 'Star + other'),
        ('GALAXY+STARS', 'Galaxy + stars'),
        ('GALAXY+OTHER', 'Galaxy + other'),
        ('QUASAR+OTHER', 'Quasar + other'),
        ('QUASAR PAIR', 'Quasar pair'),
        ('QUASAR+GALAXY', 'Quasar + galaxy'),
        ('SINGLE QUASAR', 'Single quasar'),
        ('GALAXY', 'Single galaxy'),
        ('GALAXIES', 'Galaxies'),
        ('GALAXY PAIR', 'Pair of galaxies'),
        ('QUASAR+HOST', 'Quasar + host'),
        ('PROJECTED GALAXIES', 'Projected Galaxies'),
        ('PROJECTED GALAXY + QUASAR', 'Projected galaxy + quasar'),
        ('RING GALAXY', 'Ring Galaxy'),
        ('PLANETARY NEBULA', 'Ring Galaxy'),
        ('QUASAR', 'Single quasar')
    )
    contaminant_type = MultiSelectField(max_length=100,
                                   blank=True,
                                   null=True,
                                   verbose_name="Contaminant type",                                        
                                   help_text="The type of contaminant, if known. Multiple choices are possible.",
                                   choices=ContaminantTypeChoices)

    # Fields to report updates on
    FIELDS_TO_CHECK = ['ra','dec','name','alt_name','flag','image_sep','image_conf','info','n_img','mugshot','lens_type','source_type','contaminant_type','owner','access_level']

    
    proximate = ProximateLensManager()

    
    class Meta():
        db_table = "lenses"
        verbose_name = "Lens"
        verbose_name_plural = "Lenses"
        ordering = ["ra"]
        # The constraints below should encompass both field Validators above, and the clean method below.
        constraints = [
            CheckConstraint(check=Q(n_img__range=(2,20)),name='n_img_range'),
            CheckConstraint(check=Q(ra__range=(0,360)),name='ra_range'),
            CheckConstraint(check=Q(dec__range=(-90,90)),name='dec_range'),
            CheckConstraint(check=Q(image_sep__range=(0,100)),name='image_sep_range')
        ]


    def __init__(self, *args, **kwargs):
        # Call the superclass first; it'll create all of the field objects.
        super(Lenses, self).__init__(*args, **kwargs)
        for field in self._meta.fields:
            method_name = "get_{0}_help_text".format(field.name)
            curried_method = curry(self._get_help_text,field_name=field.name)
            setattr(self, method_name, curried_method)
            method_name = "get_{0}_label".format(field.name)
            curried_method = curry(self._get_label,field_name=field.name)
            setattr(self, method_name, curried_method)

            
    def clean(self):
        try:
            self.clean_fields()
        except ValidationError as e:
            pass
        else:
            if self.ra and self.dec:
                jname = self.create_name()
                if not self.name:
                    self.name = jname
                else:
                    if not self.alt_name:
                        self.alt_name = jname
                    else:
                        altnames = [name.strip() for name in self.alt_name.split(',')]
                        if jname not in altnames:
                            altnames.append(jname)
                            self.alt_name = ', '.join(altnames)
                    
        if self.contaminant_type and self.flag != 'CONTAMINANT':
            raise ValidationError("To set the Contaminant Type the lens must be flagged as a Contaminant.")

                    
            
    def save(self,*args,**kwargs):
        if self._state.adding:
            super(Lenses,self).save(*args,**kwargs)
        else:
            dirty = self.get_dirty_fields(verbose=True,check_relationship=True)

            if "access_level" in dirty.keys():
                if dirty["access_level"]["saved"] == "PRI" and dirty["access_level"]["current"] == "PUB":
                    action.send(self.owner,target=self,verb='MakePublicLog',level='warning')
                else:
                    action.send(self.owner,target=self,verb='MakePrivateLog',level='warning')
                dirty.pop("access_level",None) # remove from any subsequent report

            if "owner" in dirty.keys():
                action.send(self.owner,target=self,verb='CedeOwnershipLog',level='info',previous_id=dirty["owner"]["saved"],next_id=dirty["owner"]["current"])
                dirty.pop("owner",None) # remove from any subsequent report

            if "mugshot" in dirty.keys():
                action.send(self.owner,target=self,verb='ImageChangeLog',level='info')
                dirty.pop("mugshot",None) # remove from any subsequent report
                
            if len(dirty) > 0:
                action.send(self.owner,target=self,verb='UpdateLog',level='info',fields=json.dumps(dirty))

            super(Lenses,self).save(*args,**kwargs)

                
        # Create new file and remove old one
        fname = self.mugshot.name
        dum,file_ext = os.path.splitext(fname)
        sled_fname = self.mugshot.field.upload_to + "/" + str( self.pk ) + file_ext
        if fname != sled_fname:
            default_storage.copy(fname,sled_fname)
            self.mugshot.name = sled_fname
            super(Lenses,self).save(*args,**kwargs)
            default_storage.mydelete(fname)

            
    def __str__(self):
        return self.name

    
    def _get_help_text(self,field_name):
        """Given a field name, return it's help text."""
        for field in self._meta.fields:
            if field.name == field_name:
                return field.help_text

            
    def _get_label(self,field_name):
        """Given a field name, return it's label."""
        for field in self._meta.fields:
            if field.name == field_name:
                return '<label>' + field.verbose_name + '</label>'

            
    def create_name(self):
        c = SkyCoord(ra=self.ra*u.degree, dec=self.dec*u.degree, frame='icrs')
        return 'J'+c.to_string('hmsdms')
        
        
    def get_absolute_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.id})

    
    def get_DB_neighbours(self,radius):
        neighbours = list(Lenses.objects.filter(access_level='PUB').annotate(distance=Func(F('ra'),F('dec'),self.ra,self.dec,function='distance_on_sky',output_field=FloatField())).filter(distance__lt=radius))
        return neighbours


    def get_latest_activity(self):
        qset = self.target_actions.all().order_by('-timestamp')
        if qset:
            return qset.first()
        else:
            return None

        
    @staticmethod
    def distance_on_sky(ra1,dec1,ra2,dec2):
        """
        This is the same implementation of the distance between a points on a sphere and the lens as the function 'distance_on_sky' in the database.

        Attributes:
            ra1,dec1 (`float`): the ra and dec of a point on the sphere. If not given, then the lens coordinates are used.
            ra2,dec2 (`float`): the ra and dec of another point.

        Returns:
            distance (`float`): the distance between the lens and the given point in arcsec.
        """
        dec1_rad = math.radians(dec1);
        dec2_rad = math.radians(dec2);
        Ddec = abs(dec1_rad - dec2_rad);
        Dra = abs(math.radians(ra1) - math.radians(ra2));
        a = math.pow(math.sin(Ddec/2.0),2) + math.cos(dec1_rad)*math.cos(dec2_rad)*math.pow(math.sin(Dra/2.0),2);
        d = math.degrees( 2.0*math.atan2(math.sqrt(a),math.sqrt(1.0-a)) )
        return d*3600.0

    
    def compare(self, obj):
        included_keys = ['alt_name',
                         'flag',
                         'score',
                         'lens_type',
                         'source_type',
                         'contaminant_type',
                         'image_conf',
                         'image_sep',
                         'info',
                         'n_images',
                         'mugshot'
                         ]
        return self._compare(self, obj, included_keys)

    def _compare(self, obj1, obj2, included_keys):
        d1, d2 = obj1.__dict__, obj2.__dict__
        old, new = {}, {}
        for k,v in d1.items():
            if k not in included_keys:
                continue
            try:
                if v != d2[k]:
                    old.update({k: v})
                    new.update({k: d2[k]})
            except KeyError:
                old.update({k: v})
        
        return old, new


    def has_access(self,user):
        if self.access_level == "PUB":
            return True
        else:
            qset_users = get_users_with_perms(self,with_group_users=True,only_with_perms_in=['view_lenses'])
            return qset_users.filter(id=user.id).exists()

        
