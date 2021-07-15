from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from enum import Enum
from enumfields import EnumField

#see here https://django-guardian.readthedocs.io/en/stable/userguide/custom-user-model.html
from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import get_objects_for_user
from guardian.shortcuts import assign_perm, remove_perm
import sys
sys.path.append('..')
import lenses
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
    affiliation = models.CharField(max_length=100, help_text="An affiliation, e.g. an academic or research institution etc.")

    def isOwner(self, single_object):
        if str(single_object.owner_id) == str(self.username):
            return True
        else:
            return False
    
    def getOwnerInfo(self, object_types=None):
        if object_types == None:
            object_types = objects_with_owner
        objects = {}
        for table in object_types:
            objects[table] = getattr(lenses.models,table).objects.filter(owner__username=self.username)
        return objects
        # Purpose: to provide all objects from a specific type, or all types, that a user owns.
        # Input: object_types has to be a sub-array of objects_with_owner. If None then use the latter.
        # Output: a corresponding dictionary of QuerySets selected with owner_id = self.id

    def getOwnedLenses(self):
        '''
        This function is for simplicity of accessing in a django template, where returning a query set is best
        '''
        objects = getattr(lenses.models,'Lenses').objects.filter(owner__username=self.username)
        return objects

    def getGroups(self):
        '''
        This function is for simplicity of accessing in a django template, where returning a query set is best
        '''
        user = Users.objects.get(username=self.username)
        groups = SledGroups.objects.filter(user=user)
        return groups

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
            single_object.owner = heir
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
    """
    This is a **base** class that encapsulates all the variables and functionality that is common across all the primary models with which we populate our database.

    Attributes:
        owner (`User`): Every instance of a primary model must have an owner. This attribute is an instance of a `User` model that corresponds to the owner of the `SingleObject` instance.
        created_at (`datetime`): The time when this object instance was created.
        modified_at (`datetime`): The time of the most recent modification/update to this object instance.
        access_level (`enum`): Determines if the object is public ('pub') or private ('pri').

    Todo:
        - We need to learn more about the ForeignKey options. E.g. when a user is deleted, a cede_responsibility should be called, see SET()?
        - WE SHOULD RENAME THIS OWNER EVERYWHERE, since this has the attribute id in django, i.e currently need owner_id_id
    """

    owner = models.ForeignKey(Users,on_delete=models.CASCADE) 
    created_at = models.DateField(auto_now_add=True)
    modified_at = models.DateField(auto_now=True)
    access_level = EnumField(AccessLevel,help_text="Set public or private access to this object.")
    
    class Meta:
        abstract = True
        get_latest_by = ["modified_at","created_at"]
        
    def isOwner(self, user):
        """
        Checks if the provided `User` is the owner.

        Args:
            user (`User`): An instance of a `User` object.

        Returns:
            bool: True if the given user is the owner, False otherwise.
        """
        if user.id == self.owner_id:
            return True
        else:
            return False

    def getCreatedAt():
        """
        Return:
           datetime: A formatted datetime string of the `created_at` attribute.
        """
        return self.created_at

    def getModifiedAt():
        """
        Return:
           datetime: A formatted datetime string of the `modified_at` attribute.
        """
        return self.modified_at


    # def getOwnerInfo():

    # def getLink():

    # def addToCollection():




    

class SledGroups(Group):
    """
    The custom SLED model for a group of users, inheriting from the django `Group`.

    Attributes:
        description(`str`): A short description of the group's purpose.

    Todo:
        - Should this be a SingleObject? If so then the access_level should always be set to public and we will not be using access related functions.
        - Related to the above, it doesn't make sense to have collections of groups, so no need to use the addToCollection, etc, functions.

    """
    description = models.CharField(max_length=180,null=True, blank=True)
    
    class Meta():
        db_table = "sledgroups"
        verbose_name = "sledgroup"
        verbose_name_plural = "sledgroups"

    def getAllMembers(self):
        """
        Note:
            We may want to restrict this function to the owner, or to members only
        """
        users = self.user_set.all()
        return users
        
    def addMember(self,owner,seld_user):
        if owner.isOwner(self) and not sled_user.groups.filter(name=self.name):
            self.user_set.add(sled_user)
        
    def removeMember(self,owner,sled_user):
        if owner.isOwner(self) and sled_user.groups.filter(name=self.name):
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
