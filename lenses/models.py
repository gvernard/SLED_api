from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from enum import Enum
from enumfields import EnumField

#see here https://django-guardian.readthedocs.io/en/stable/userguide/custom-user-model.html
from guardian.core import ObjectPermissionChecker
from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import get_objects_for_user, assign_perm, remove_perm
import sys
sys.path.append('..')
import lenses

# Dummy array containing the primary objects in the database. Should be called from a module named 'constants.py' or similar.
objects_with_owner = ["Lenses"]#,"Finders","Scores","ModelMethods","Models","FutureData","Data"]

### Dummy function to create a notification. The proper one should be called from the notifications module.
def create_notification(user,objects):
    object_names = [x.name for x in objects]
    if isinstance(user,Users):
        return user.username+' - '+str(len(objects))+ ' - ' + ','.join(object_names)
    elif isinstance(user,SledGroups):
        return user.name+' - '+str(len(objects))+ ' - ' + ','.join(object_names)


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
    """ The class to represent registered users within SLED.

    A SLED user can own objects with which they can interact, e.g. give access to other users, cede ownership, add/remove objects from owned collections, etc.

    SLED users can also be added into groups, none or several, or be the owners of groups (of which they are members).
    
    Attributes:
        affiliation (`CharField`): Affiliation is the only field in addition to the standard django `User` fields. User groups (see ~SledGroups) are taken care of by the existing django modules.
    """
    affiliation = models.CharField(max_length=100, help_text="An affiliation, e.g. an academic or research institution etc.")

    def getOwnedObjects(self, user_object_types=None):
        """
        Provides access to all the objects that the user owns, arranged by type.

        Args:
            user_object_types (optional[List[str]]): A list of strings matching the names of the primary model database tables.
            The list is filtered to keep only those provided names that indeed correspond to primary models.
            If `None` then all the primary models are used.

        Returns:
            dict: The keys are the same as the filtered input object_types, or the entire list of `objects_with_owner`.
            The values are QuerySets corresponding to a query in each primary model table with the owner_id set to this user.
        """
        if user_object_types == None:
            filtered_object_types = objects_with_owner
        else:
            filtered_object_types = [x for x in user_object_types if x in objects_with_owner]
        objects = {}
        for table in filtered_object_types:
            objects[table] = getattr(lenses.models,table).objects.filter(owner__username=self.username)
        return objects

    ### This function is superceded by the one above (getOwnedObjects)
    # def getOwnedLenses(self):
    #     '''
    #     This function is for simplicity of accessing in a django template, where returning a query set is best
    #     '''
    #     objects = getattr(lenses.models,'Lenses').objects.filter(owner__username=self.username)
    #     return objects

    def getGroupsIsMember(self):
        """
        Provides access to all the SledGroups that the user is a member of.

        Returns:
            A QuerySet to match the groups the user is a member of.
        """
        user = Users.objects.get(username=self.username)
        groups = SledGroups.objects.filter(user=user)
        return groups


    
    def giveAccess(self,objects,target_users):
        """
        Gives access to the primary object(s) that are owned by the user to a list of users or groups.

        First, this function performs a check that the user is indeed the owner of all the provided objects and raises an exception if not.
        Then, a cross match is performed between users/groups and objects to find to how many new objects each user will be given access to.
        This involves 2 queries to the database per user: 1 to get any permissions for the objects, and one to update the new permissions.
        But if the user already has permissions to all the objects then the second query is not performed.

        Note:
            A given user can also be a member of a given group. In this case the user will have a 'double permission' to view the object.
            Both the individual and group permissions will have to be revoked to forbid any access.

        Args:
            single_objects (List[SingleObject]): A list of primary objects of a specific type.
            A check is performed to ensure that the user is the owner of all the objects in the list.
            target_users (List[Users or Groups]): A list of users, groups, or both.

        Returns:
            A list of notifications only to those users/groups that were just given access (i.e. didn't already have access to the objects), containing only those objects for which they were given access. If a user is also member of a group, they will be notified twice.

        Raises:
            An exception of some type when the user is not the owner of all the objects.

        Todo:
            Implement the exception and the notifications.
        """

        # If input arguments are single values, convert to lists
        if isinstance(objects,SingleObject):
            objects = [objects]
        if isinstance(target_users,Users) or isinstance(target_users,SledGroups):
            target_users = [target_users]
        #print(len(single_objects),len(target_users))

        
        # Check that user is the owner
        not_owned = []
        for obj in objects:
            if not obj.isOwner(self):
                not_owned.append(obj)
        if len(not_owned) == 0:
            # User owns all objects, proceed with giving access
            perm = "view_"+objects[0]._meta.db_table

            # first loop over the target_users
            notifications = []
            for user in target_users:
                # fetch permissions for all the objects for the given user (just 1 query)
                new_objects_per_user = []
                checker = ObjectPermissionChecker(user)
                checker.prefetch_perms(objects)            
                for obj in objects:
                    if not checker.has_perm(perm,obj):
                        new_objects_per_user.append(obj)
                # if there are objects for which this user was just granted new permission, create a notification
                print(new_objects_per_user)
                print(objects)
                if len(new_objects_per_user) > 0:
                    assign_perm(perm,user,new_objects_per_user) # (just 1 query)
                    notifications.append( create_notification(user,new_objects_per_user) )

            return notifications
        else:
            # User does NOT own all the objects, raise exception with useful information
            print('user is NOT the owner of '+str(len(not_owned))+' objects the operation should not proceed')
            



            
    def revokeAccess(self,objects,target_users):
        # If input arguments are single values, convert to lists
        if isinstance(objects,SingleObject):
            objects = [objects]
        if isinstance(target_users,Users) or isinstance(target_users,SledGroups):
            target_users = [target_users]
        #print(len(single_objects),len(target_users))
    
        # Check that user is the owner
        not_owned = []
        for obj in objects:
            if not obj.isOwner(self):
                not_owned.append(obj)
        if len(not_owned) == 0:
            # User owns all objects, proceed with revoking access
            perm = "view_"+objects[0]._meta.db_table

            # first loop over the target_users
            notifications = []
            for user in target_users:
                # fetch permissions for all the objects for the given user (just 1 query)
                checker = ObjectPermissionChecker(user)
                checker.prefetch_perms(objects)            

                revoked_objects_per_user = []
                for obj in objects:
                    if checker.has_perm(perm,obj):
                        revoked_objects_per_user.append(obj)
                # if there are objects for which this user had permissions just revoked, create a notification
                print(revoked_objects_per_user)
                print(objects)
                if len(revoked_objects_per_user) > 0:
                    print(perm)
                    print(user)
                    remove_perm(perm,user,revoked_objects_per_user) # (just 1 query)
                    #remove_perm(perm,user,objects) # (just 1 query)
                    notifications.append( create_notification(user,revoked_objects_per_user) )
               
            return notifications
        else:
            # User does NOT own all the objects, raise exception with useful information
            print('user is NOT the owner of '+str(len(not_owned))+' objects, the operation should not proceed')
            

        



            
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

    def __str__(self):
        return self.name
    
    

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
