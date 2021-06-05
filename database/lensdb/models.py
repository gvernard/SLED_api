from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from enum import Enum
from enumfields import EnumField

#see here https://django-guardian.readthedocs.io/en/stable/userguide/custom-user-model.html
from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import assign_perm, remove_perm

objects_with_owner = ["Lenses"]#,"Finders","Scores","ModelMethods","Models","FutureData","Data"]

class AccessLevel(Enum):
    pub = "public"
    pri = "private"

class ImageConf(Enum):
    NONE = ''
    CUSP = 'CUSP'
    FOLD = 'FOLD'
    CROSS = 'CROSS'
    DOUBLE = 'DOUBLE'
    QUAD = 'QUAD'
    RING = 'RING'
    ARCS = 'ARCS'

class SourceType(Enum):
    NONE = ''
    GALAXY = 'GALAXY'
    GROUP = 'GROUP'
    CLUSTER = 'CLUSTER'
    AGN = 'AGN'

class LensType(Enum):
    NONE = ''
    GALAXY = 'GALAXY'
    AGN = 'AGN'
    GW = 'GW'
    FRB = 'FRB'
    GRB = 'GRB'
    SN = 'SN'



class Users(AbstractUser,GuardianUserMixin):
    # Affiliation is the only field we need to provide ourselves, the rest, including Groups, is taken care of by the existing django modules.
    affiliation = models.CharField(max_length=100,help_text="An affiliation, e.g. an academic or research institution etc.")

    def isOwner(self,single_object):
        if str(single_object.owner_id) == str(self.username):
            return True
        else:
            return False
    
    def getOwnerInfo(object_types=None):
        if object_types == None:
            object_types = objects_with_owner
        objects = {}
        for table in object_types:
            objects[table] = getattr(lensdb.models,'table').all().filter(owner_id=self.username)
        # Purpose: to provide all objects from a specific type, or all types, that a user owns.
        # Input: object_types has to be a sub-array of objects_with_owner. If None then use the latter.
        # Output: a corresponding dictionary of QuerySets selected with owner_id = self.id

    def giveAccess(self,single_object,target):
        # 'target' is either another user or group
        # Instead of looping, we can also pass a query set or a list of model instances to asign_perm.
        perm = "view_"+single_object._meta.db_table
        if self.isOwner(single_object):
            assign_perm(perm,target,single_object)
            # Here notify the user/group that they now have access to this lens
            
    def revokeAccess(self,single_object,target):
        perm = "view_"+single_object._meta.db_table
        if self.isOwner(single_object) and target.has_perm(perm,single_object):
            remove_perm(perm,target,single_object)
            # Here notify the user/group that they do not have access to this lens anymore
            
    def makePublic(self,single_object):
        if self.isOwner(single_object) and single_object.access_level == 'private':
            single_object.access_level = 'public'
            singleObject.save()
            # Here remove any permissions to users/groups and notify them
            
    def makePrivate(self,single_object):
        if self.isOwner(single_object) and single_object.acces_level == 'public':
            # The following will have to be replaced by a confirmation task from the DB admins
            single_object.access_level = 'private'
            singleObject.save()
            
    def cedeOwnership(self,single_object,heir):
        if self.isOwner(single_object) and heir.is_active():
            # The following will have to be replaced by a confirmation task from the heir
            single_object.owner_id = heir
            single_object.save()

    ####################################################################
    # Below this point lets put actions relevant only to the admin users
    def deactivateUser(self,user):
        # See django documentation for is_active for login and permissions
        if self.is_staff() and user.is_active():
            user.is_active = False
            user.save()

    def activateUser(self,user):
        # See django documentation for is_active for login and permissions
        if self.is_staff() and not user.is_active():
            user.is_active = True
            user.save()
    
    pass



    
class SingleObject(models.Model):
    # We need to learn more about the ForeignKey options. E.g. when a user is deleted, a cede_responsibility should be called, see SET()?
    owner_id = models.ForeignKey(Users,on_delete=models.CASCADE)
    created_at = models.DateField(auto_now_add=True)
    modified_at = models.DateField(auto_now=True)
    access_level = EnumField(AccessLevel,help_text="Set public or private access to this object.")

    class Meta:
        abstract = True
        get_latest_by = ["modified_at","created_at"]
        
    def isOwner(user_id):
        if user_id == self.owner_id:
            return True
        else:
            return False

    def getModifiedAt():
        return self.modified_at

    def getCreatedAt():
        return self.created_at

    # def getOwnerInfo():

    # def getLink():

    # def addToCollection():




    

class SledGroups(Group):
    # The group name field is inherited from the Group object.
    # The access_level should always be set to public.
    # Hence, from the SingleObject base class we will neither use the access related functions, e.g. setAccessLevel or setAccess, nor the addToCollection function.
    #owner_id = models.ForeignKey(Users,db_index=False,on_delete=models.CASCADE)
    description = models.CharField(max_length=180,null=True, blank=True)

    class Meta():
        db_table = "sledgroups"
        verbose_name = "sledgroup"
        verbose_name_plural = "sledgroups"

    def getAllMembers(self):
        users = self.user_set.all()
        return users
        
    def addMember(self,seld_user):
        self.user_set.add(sled_user)
        
    def removeMember(self,sled_user):
        self.user_set.remove(sled_user)


    
    

class AccessibleLensManager(models.Manager):
    def all(self,user):
        # Attention: this is inefficient because it makes two queries to the database, one for the public and one for the private lenses. We need to replace this with one.
        lenses_public  = super().get_queryset().filter(access_level='public')
        lenses_private = super().get_queryset().filter(access_level='private')
        accessible_private_lenses = get_objects_for_user(user,'view_lenses',klass = lenses_private)
        return lenses_public | accessible_private_lenses # merge and return querysets


# Privileges:
# - anonymous user can only view (in the web interface, cannot download JSON, etc)
# - AUTH_user can insert
# - owner can update
# - admin can update and delete
class Lenses(SingleObject):
    ra = models.DecimalField(max_digits=7, decimal_places=4, help_text="The RA of the lens [degrees].") # validators or constraints in Meta?
    dec = models.DecimalField(max_digits=6, decimal_places=4, help_text="The DEC of the lens [degrees].")
    name = models.CharField(max_length=100, help_text="An identification for the lens, e.g. the usual phone numbers.")
    # alt_name = models.CharField(max_length=100,help_text="A colloquial name with which the lens is know, e.g. 'The Einstein cross', etc.")  # This could become a comma separated list of names.
    # image_sep = models.DecimalField(max_digits=4,decimal_places=2,help_text="An estimate of the maximum image separation or arc radius [arcsec].",validators=[MinValueValidator(0.0)]) # DecimalField calls DecimalValidator
    # z_source = models.DecimalField(blank=True,max_digits=4,decimal_places=3,help_text="The redshift of the source, if known.",validators=[MinValueValidator(0.0)])
    # z_lens = models.DecimalField(blank=True,max_digits=4,decimal_places=3,help_text="The redshift of the lens, if known.",validators=[MinValueValidator(0.0)])
    # image_conf = models.CharField(blank=True,max_length=10,choices=ImageConf.choices,default=ImageConf.NONE,help_text="Multiple image and extended lensed features configuration.")
    # lens_type = models.CharField(blank=True,max_length=10,choices=LensType.choices,default=LensType.NONE,help_text="Lens object type.")
    # source_type = models.CharField(blank=True,max_length=10,choices=SourceType.choices,default=SourceType.NONE,help_text="Source object type.")
    # flag_confirmed = models.BooleanField(default=False,blank=True,help_text="Set to true if the lens has been confirmed by a publication.") # Do we need to associate a paper directly (ForeignKey) instead of Booelan? We can have both confirmed and contaminant set to true :)
    # flag_contaminant = models.BooleanField(default=False,blank=True,help_text="Set to true if the object has been confirmed as not a lens by a publication.")
    # discovered_at = models.DateField(help_text="The date when the lens was discovered, or the discovery paper published.")
    # info = TextField(help_text="Description of any important aspects of this system, e.g. discovery/interesting features/multiple discoverers/etc.")

    
    accessible_objects = AccessibleLensManager() # the first manager is the default one
    objects = models.Manager()
    
    class Meta():
        db_table = "lenses"
        ordering = ["ra"]
        unique_together = ["ra","dec"]
        constraints = [
            # Reiterate the validators
            # z_lens must be > lens_source
        ]
        verbose_name = "lens"
        verbose_name_plural = "lenses"

    def __str__(self):
        return self.name # or return some 'phone-number' if this name is not set

#    class Meta:
#        # django creates automatically the permissions we want, see the Note in blue here: https://django-guardian.readthedocs.io/en/stable/userguide/assign.html
#        permissions = (
#            ('has_access', 'Has access'),
#        )

