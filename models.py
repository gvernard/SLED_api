from django.db import models
from django.contrib.auth.models import AbstractUser,Group

objects_with_owner = ["Lenses","Finders","Scores","ModelMethods","Models","FutureData","Data"]



    
class SingleObject(models.Model):
    owner_id = models.ForeignKey(SledUsers,db_index=False,on_delete=models.CASCADE)
    # We need to learn more about the ForeignKey options. E.g. when a user is deleted, a cede_responsibility should be called, see SET()?
    created_at = models.DateField(auto_now_add=True)
    modified_at = models.DateField(auto_now=True)
    access_level =  EnumField(choices=[
      ('public', 'Public access'),
      ('private', 'Private access')
    ],help_text="Set the access to this object.")

    
    class Meta:
        abstract = True
        managed = False
        get_latest_by = ["modified_at","created_at"]


        
    def isOwner(user_id):
        if user_id == self.owner_id:
            return True
        else:
            return False

    def getOwnerInfo():

    def setOwner(user_id,other_user_id):
        if self.isOwner(user_id) and user_id != other_user_id:
             call cede_responsibility
        else:
            # cannot setOwner, user is not the owner

    def getModifiedAt():
        return self.modified_at

    def getCreatedAt():
        return self.created_at

    def getLink():


    # Function that require access_table query
    def setAccessLevel():

    def setAccess():

    def addToCollection():
        



# Types of users: anonymous, authenticated, inactive
# User roles: owner, admin
class SledUser(AbstractUser):
    affiliation = models.CharField(max_length=100,help_text("An affiliation, e.g. an academic or research institution etc."))
    group_ids = list( self.groups.values_list('id',flat=True) ) # Store all the user groups here for convenience

    
    def getOwnership(object_types=None):
        # Purpose: to provide all objects from a specific type, or all types, that a user owns.
        # Input: one or more of the objects_with_owner list. If None then use the whole list.
        # Output: a corresponding dictionary of QuerySets selected with owner_id = self.id

    def cedeOwnership(object_type,object_ids=None,heir_id):
        # Purpose: to cede ownership of some or all of the objects of a specific type that a user owns.
        # Input: the object type, a list of object ids (if empty then all objects are selected), another user id
        # Output: An action notification for the heir with a json object attached that holds the validated information of the query.
        #         Returns a QuerySet of any objects that will not be updated (becacuse the user is not the owner)
        # Notes: Verify the object_ids with a query having object_id in [object_ids] GROUP BY owner_id. If the returned number of objects with this user as owner
        #        is smaller than len(object_ids), return the QuerySet with the different owners. We need to temporarily block the user from updating the object_ids.
        # Confirmation action: The heir will be notified with a YesNo action. If yes, then give update privileges to the heir for the object_ids and run the update to change the owner.
        #                      If no, then restore the update permission to the user and send email notification.
        # Problems: maybe use a QuerySet that contains the objects already as input?

    def cedeOwnershipAll(object_type,heir_id):
        # The main difference with the above function is that it doesn't need any object ids, it selects all the objects owned by the user.
        # The user will need to confirm that ALL the objects they own will be transfered, but this doesn't have to happen in this function (probably in the web interface).

    def deactivateUser():
        # The most important task before making a user inactive is to cede the ownership to other users.
        # If the user is an admin, maybe more tasks will need to be performed.


class SledUserGroup(Group):
    owner_id = models.ForeignKey(SledUser,db_index=False,on_delete=models.CASCADE)
    description = models.TextField(help_text="Group description, member rules, etc.")
    







class AccessibleLensManager(models.Manager):
    def all():
        # This needs a user object as input
        # return only the juicy lens fields (no metadata like the SingleObject fields)
        lenses_public = # Query the lens table with access_level set to public
        lenses_private = # Same query as above JOIN on object id with the access table where object=lens and access_user_id=user_id OR access_user_id IN user.groups

        
# Privileges:
# - anonymous user can only view (in the web interface, cannot download JSON, etc)
# - AUTH_user can insert
# - owner can update
# - admin can update and delete
# Notes: we need permissions on a per-object basis (to view and to update)
class Lens(SingleObject):
    class ImageConf(models.TextChoices):
        NONE = '',_('unknown')
        CUSP = 'CUSP', _('Cusp')
        FOLD = 'FOLD', _('Fold')
        CROSS = 'CROSS', _('Cross')
        DOUBLE = 'DOUBLE', _('Double')
        QUAD = 'QUAD', _('Quad')
        RING = 'RING', _('Ring')
        ARCS = 'ARCS', _('Arcs')

    class SourceType(models.TextChoices):
        NONE = '',_('unknown')
        GALAXY = 'GALAXY',_('Galaxy')
        GROUP = 'GROUP',_('Group')
        CLUSTER = 'CLUSTER',_('Cluster')
        AGN = 'AGN',_('AGN')

    class LensType(models.TextChoices):
        NONE = '',_('unknown')
        GALAXY = 'GALAXY',_('Galaxy')
        AGN = 'AGN',_('AGN')
        GW = 'GW',_('Gravitational wave')
        FRB = 'FRB',_('Fast Radio Burst')
        GRB = 'GRB',_('Gamma-Ray Burst')
        SN = 'SN',_('Supernova')        
        
    ra = models.DecimalField(max_digits=7,decimal_places=4,help_text="The RA of the lens [degrees].",validators=[MaxValueValidator(360.0),MinValueValidator(0.0)])
    dec = models.DecimalField(max_digits=6,decimal_places=4,help_text="The DEC of the lens [degrees].",validators=[MaxValueValidator(90.0),MinValueValidator(-90.0)])
    name = models.CharField(max_length=100,help_text="The official name/code name of the lens.") # Custom validator for the name?
    alt_name = models.CharField(max_length=100,help_text="A colloquial name with which the lens is know, e.g. 'The Einstein cross', etc.")
    image_sep = models.DecimalField(max_digits=4,decimal_places=2,help_text="An estimate of the maximum image separation or arc radius [arcsec].",validators=[MinValueValidator(0.0)]) # DecimalField calls DecimalValidator
    z_source = models.DecimalField(blank=True,max_digits=4,decimal_places=3,help_text="The redshift of the source, if known.",validators=[MinValueValidator(0.0)])
    z_lens = models.DecimalField(blank=True,max_digits=4,decimal_places=3,help_text="The redshift of the lens, if known.",validators=[MinValueValidator(0.0)])
    image_conf = models.CharField(blank=True,max_length=10,choices=ImageConf.choices,default=ImageConf.NONE,help_text="Multiple image and extended lensed features configuration.")
    lens_type = models.CharField(blank=True,max_length=10,choices=LensType.choices,default=LensType.NONE,help_text="Lens object type.")
    source_type = models.CharField(blank=True,max_length=10,choices=SourceType.choices,default=SourceType.NONE,help_text="Source object type.")
    flag_confirmed = models.BooleanField(default=False,blank=True,help_text="Set to true if the lens has been confirmed by a publication.") # Do we need to associate a paper directly (ForeignKey) instead of Booelan? We can have both confirmed and contaminant set to true :)
    flag_contaminant = models.BooleanField(default=False,blank=True,help_text="Set to true if the object has been confirmed as not a lens by a publication.")
    discovered_at = models.DateField(help_text="The date when the lens was discovered, or the discovery paper published.")
    info = TextField(help_text="Description of any important aspects of this system, e.g. discovery/interesting features/multiple discoverers/etc.")

    objects = models.Manager()
    accessible_objects = AccessibleLensManager()
    
    class Meta(SingleObject.Meta):
        db_table = "lenses"
        ordering = ["ra"]
        unique_together = ["ra","dec"]
        constraints = [
            # Reiterate the validators
            # z_lens must be > lens_source
        ]
        verbose_name = "lens"
        verbose_name_plural = "lenses"



