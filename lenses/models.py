from django.db import models
from django import forms
from django.contrib.auth.models import AbstractUser, Group
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.urls import reverse
from django.db.models import F, Func, FloatField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

#see here https://django-guardian.readthedocs.io/en/stable/userguide/custom-user-model.html
from guardian.core import ObjectPermissionChecker
from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import *

from multiselectfield import MultiSelectField

from notifications.signals import notify


import abc
from operator import itemgetter
import sys
sys.path.append('..')
import lenses
import inspect
import json
import math
from astropy import units as u
from astropy.coordinates import SkyCoord



# Dummy array containing the primary objects in the database. Should be called from a module named 'constants.py' or similar.
objects_with_owner = ["Lenses","ConfirmationTask"]#,"Finders","Scores","ModelMethods","Models","FutureData","Data"]






class Users(AbstractUser,GuardianUserMixin):
    """ The class to represent registered users within SLED.

    A SLED user can own objects with which they can interact, e.g. give access to other users, cede ownership, add/remove objects from owned collections, etc.

    SLED users can also be added into groups, none or several, or be the owners of groups (of which they are members).
    
    Attributes:
        affiliation (`CharField`): Affiliation is the only field in addition to the standard django `User` fields. User groups (see ~SledGroups) are taken care of by the existing django modules.
    """
    affiliation = models.CharField(max_length=100, help_text="An affiliation, e.g. an academic or research institution etc.")

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('users:user_profile')
    
    def getOwnedObjects(self, user_object_types=None):
        """
        Provides access to all the objects that the user owns, arranged by type.

        Args:
            user_object_types (optional[List[str]]): A list of strings matching the names of the primary model database tables.
            The list is filtered to keep only those provided names that indeed correspond to primary models.
            If `None` then all the primary models are used.

        Returns:
            dict: The keys are the same as the filtered input object_types, or the entire list of `objects_with_owner`.
            The values are `QuerySets` corresponding to a query in each primary model table with the owner_id set to this user.
        """
        if user_object_types == None:
            filtered_object_types = objects_with_owner
        else:
            filtered_object_types = [x for x in user_object_types if x in objects_with_owner]
        objects = {}
        for table in filtered_object_types:
            objects[table] = getattr(lenses.models,table).objects.filter(owner__username=self.username)
        return objects


    def getGroupsIsMember(self):
        """
        Provides access to all the SledGroups that the user is a member of.

        Returns:
            A QuerySet to match the groups the user is a member of.
        """
        user = Users.objects.get(username=self.username)
        groups = SledGroups.objects.filter(user=user)
        return groups

    def checkOwnsList(self,objects):
        """
        Finds any objects in the given list that are not owned by the user.

        Args:
            objects(List[SingleObject]): A list of primary objects of a specific type.

        Raises:
            AssertionError: If the provided list contains objects that the user does not own.
        """
        not_owned = []
        for obj in objects:
            if not obj.isOwner(self):
                not_owned.append(obj)
        try:
            assert (len(not_owned) == 0), "User "+self.username+" is NOT the owner of "+str(len(not_owned))+" objects in the list."
        except AssertionError as error:
            print(error)
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print("The operation of '"+caller[1][3]+"' should not proceed")

    def giveAccess(self,objects,target_users):
        """
        Gives access to the primary object(s) that are owned by the user to a list of users or groups.

        First, this function performs a check that the user is indeed the owner of all the provided objects and raises an exception if not.
        Then, a cross match is performed between users/groups and objects to find to how many new objects each user will be given access to.
        This involves 2 queries to the database per user: 1 to get any permissions for the objects, and one to update the new permissions.
        But if the user already has permissions to all the objects then the second query is not performed.
        Finally, each user is notified with which objects they have been granted access to.

        Note:
            A given user can also be a member of a given group. In this case the user will have a 'double permission' to view the object.
            Both the individual and group permissions will have to be revoked to forbid any access.

        Args:
            objects (List[SingleObject]): A list of primary objects of a specific type. A check is performed to ensure that the user is the owner of all the objects in the list.
            target_users (List[Users or Groups]): A list of users, groups, or both.
        """

        # If input arguments are single values, convert to lists
        if isinstance(objects,SingleObject):
            objects = [objects]
        if isinstance(target_users,Users) or isinstance(target_users,SledGroups):
            target_users = [target_users]
        if self in target_users:
            target_users.remove(self)
        # Check that user is the owner
        self.checkOwnsList(objects)

        # User owns all objects, proceed with giving access
        perm = "view_"+objects[0]._meta.db_table

        # first loop over the target_users
        for user in target_users:
            print(type(user))
            # fetch permissions for all the objects for the given user (just 1 query)
            new_objects_per_user = []
            new_objects_per_user_ids = []
            checker = ObjectPermissionChecker(user)
            checker.prefetch_perms(objects)
            object_type = objects[0]._meta.model.__name__
            for obj in objects:
                if not checker.has_perm(perm,obj):
                    new_objects_per_user.append(obj)
                    new_objects_per_user_ids.append(obj.id)
            # if there are objects for which this user was just granted new permission, create a notification
            if len(new_objects_per_user) > 0:
                assign_perm(perm,user,new_objects_per_user) # (just 1 query)
                if isinstance(user,Users):
                    notify.send(sender=self,recipient=user,verb='You have been granted access to private objects',level='success',timestamp=timezone.now(),note_type='GiveAccess',object_type=object_type,object_ids=new_objects_per_user_ids)
                else:
                    notify.send(sender=self,recipient=user,verb='Your group "'+user.name+'" has been granted access to private objects',level='success',timestamp=timezone.now(),note_type='GiveAccess',object_type=object_type,object_ids=new_objects_per_user_ids)            


    def revokeAccess(self,objects,target_users):
        """
        Revokes 'view' permission of the 'target_users' from the given 'objects'.

        Checks that the user is the owner of all the provided objects first.
        Notifies those users/groups whose 'view' permission was just revoked, containing only affected objects. If a user is also member of a group, they will be notified twice.

        Args:
            objects(List[SingleObject]): A list of primary objects of a specific type.
            target_users(List[User or SledGroup]): A list of Users, or Sledgroups, or mixed.
        """
        # If input argument 'objects' is a single value, convert to list
        if isinstance(objects,SingleObject):
            objects = [objects]
        # Check that user is the owner
        self.checkOwnsList(objects)
        # If input argument 'target_users' is a single value, convert to list
        if isinstance(target_users,Users) or isinstance(target_users,SledGroups):
            target_users = [target_users]
        if self in target_users:
            target_users.remove(self)
            
        # User owns all objects, proceed with revoking access
        perm = "view_"+objects[0]._meta.db_table

        # first loop over the target_users
        for user in target_users:
            # fetch permissions for all the objects for the given user (just 1 query)
            checker = ObjectPermissionChecker(user)
            checker.prefetch_perms(objects)            
            object_type = objects[0]._meta.model.__name__
            revoked_objects_per_user_ids = []
            for obj in objects:
                if checker.has_perm(perm,obj):
                    revoked_objects_per_user_ids.append(obj.id)
            # if there are objects for which this user had permissions just revoked, create a notification
            if len(revoked_objects_per_user_ids) > 0:
                remove_perm(perm,user,Lenses.objects.filter(id__in=revoked_objects_per_user_ids)) # (just 1 query)
                if isinstance(user,Users):
                    notify.send(sender=self,recipient=user,verb='Your access to private objects has been revoked',level='warning',timestamp=timezone.now(),note_type='RevokeAccess',object_type=object_type,object_ids=revoked_objects_per_user_ids)
                else:
                    notify.send(sender=self,recipient=user,verb=user.name+'\'s group access to private objects has been revoked',level='warning',timestamp=timezone.now(),note_type='RevokeAccess',object_type=object_type,object_ids=revoked_objects_per_user_ids)


    def accessible_per_other(self,objects,mode):
        """
        Given a list of PRIVATE objects OWNED by the user, this function finds who else has access to them.
        The output is arranged per username.

        Args:
            objects(List[SingleObject]): a list of OWNED and PRIVATE objects for which the user-owner needs to find who else has access to.
            flag ('users' or 'groups'): a flag to determine whether access is checked on an individual users or group basis.
        Return:
            ugs(List[`Users`]): a list of users or groups that have access to the objects
            accessible_objects(List[int]): a list of lists. One list per entry of 'ugs' that contains the indices of the input list, i.e. a subset of it, that the user, or group, has access to. 
        """
        # If input argument is a single value, convert to list
        if isinstance(objects,SingleObject):
            objects = [objects]
        # Check that user is the owner
        self.checkOwnsList(objects) 
        
        try:
            # Check that all objects are indeed private.
            flag = True
            for obj in objects:
                if obj.access_level == 'PUB':
                    flag = False
            assert(flag),"All given objects MUST be private, but it's not the case."
        except AssertionError as error:
            print(error)
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print("The operation of '"+caller[1][3]+"' should not proceed")
        else:
            all_ugs = []
            ug_obj_pairs = []
            for i in range(0,len(objects)):
                if mode == 'users':
                    ugs = list(objects[i].getUsersWithAccess(self))
                else:
                    ugs = list(objects[i].getGroupsWithAccess(self))
                if ugs:
                    all_ugs.extend(ugs)
                    for ug in ugs:
                        ug_obj_pairs.append((ug.id,i))
            # Aggregate the objects that were changed for each user in a dcitionary with primary_key:list of indices to objs_to_update
            ug_accesses_objects = {key: list(map(itemgetter(1), ele)) for key, ele in groupby(sorted(ug_obj_pairs,key=itemgetter(0)), key = itemgetter(0))}
            unique_ugs = set(all_ugs)
            accessible_objects = []
            for ug in unique_ugs:
                    accessible_objects.append(ug_accesses_objects[ug.id])
            #print(unique_ugs,accessible_objects)
            return unique_ugs,accessible_objects


        
    def makePublic(self,objects):
        """
        Changes the access_level of the given objects to private.

        First makes sure that the user owns all the objects, then updates only those objects that are private with a single query to the database.

        Args:
            objects(List[SingleObject]): A list of primary objects of a specific type.

        Returns:
            to_check(List[SingleObject]): A subset of the input objects, those that have close neighbours already existing in the database (possible duplicates)
        """
        # If input argument is a single value, convert to list
        if isinstance(objects,SingleObject):
            objects = [objects]
        # Check that user is the owner
        self.checkOwnsList(objects)

        # Loop over the list, act only on those objects that are private
        objs_to_update = []
        for obj in objects:
            if obj.access_level == 'PRI':
                objs_to_update.append(obj)
        #print(objs_to_update)

        try:
            assert (len(objs_to_update)>0),"All objects are already public"
        except AssertionError as error:
            print(error)
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print("The operation of '"+caller[1][3]+"' should not proceed")
        else:
            object_type = objs_to_update[0]._meta.model.__name__
            perm = "view_"+object_type
            
            ### Very important: check for proximity before making public.
            #####################################################            
            if object_type == 'Lenses':
                indices,neis = Lenses.proximate.get_DB_neighbours_many(objs_to_update)
                if indices:
                    # Possible duplicates, return them
                    to_check = [objs_to_update[i] for i in indices]
                    return to_check
            
            ### Per user
            #####################################################            
            users_with_access,accessible_objects = self.accessible_per_other(objs_to_update,'users')
            for i,user in enumerate(users_with_access):
                obj_ids = []
                for j in accessible_objects[i]:
                    obj_ids.append(objs_to_update[j].id)
                remove_perm(perm,user,Lenses.objects.filter(id__in=obj_ids)) # Remove all the view permissions for these objects that are to be updated (just 1 query)
                notify.send(sender=self,
                            recipient=user,
                            verb='Private objects you had access to are now public.',
                            level='warning',
                            timestamp=timezone.now(),
                            note_type='MakePublic',
                            object_type=object_type,
                            object_ids=obj_ids)

            ### Per group
            #####################################################
            groups_with_access,accessible_objects = self.accessible_per_other(objs_to_update,'groups')
            for i,group in enumerate(groups_with_access):
                obj_ids = []
                for j in accessible_objects[i]:
                    obj_ids.append(objs_to_update[j].id)
                remove_perm(perm,group,Lenses.objects.filter(id__in=obj_ids)) # Remove all the view permissions for these objects that are to be updated (just 1 query)
                notify.send(sender=self,
                            recipient=group,
                            verb='Private objects you had access to are now public.',
                            level='warning',
                            timestamp=timezone.now(),
                            note_type='MakePublic',
                            object_type=object_type,
                            object_ids=obj_ids)

            # Finally, update only those objects that need to be updated in a single query
            #####################################################
            for obj in objs_to_update:
                obj.access_level = 'PUB'
            getattr(lenses.models,'Lenses').objects.bulk_update(objs_to_update,['access_level'])

            # return an empty list to indicate that everything went fine (if neighbours are found, they are returned)
            return []
                
    def makePrivate(self,objects,justification=None):
        """
        Changes the AccessLevel of the given objects to 'private'.
        
        First makes sure that the user owns all the objects, then creates a confirmation task for the database admin.

        Args:
            objects(List[SingleObject]): A list of primary objects of a specific type.

        Returns:
            task: A confirmation task
        """
        # If input argument is a single value, convert to list
        if isinstance(objects,SingleObject):
            objects = [objects]
        # Check that user is the owner
        self.checkOwnsList(objects)

        cargo = {}
        cargo["object_type"] = objects[0]._meta.model.__name__
        ids = []
        for obj in objects:
            ids.append(obj.id)
        cargo["object_ids"] = ids
        cargo["comment"] = justification

        # This line needs to be replaced with the DB admin
        mytask = ConfirmationTask.create_task(self,Users.getAdmin(),'MakePrivate',cargo)
        return mytask 
      
    def cedeOwnership(self,objects,heir,justification=None):
        """
        Changes the owner of the given objects to the heir.
        
        First makes sure that the user owns all the objects, then creates a confirmation task for the heir.

        Args:
            objects(List[SingleObject]): A list of primary objects of a specific type.
            heir (`Queryset`): A Queryset consisting of only one user

        Returns:
            task: A confirmation task
        """
        # If input argument is a single value, convert to list
        if isinstance(objects,SingleObject):
            objects = [objects]
        # Check that user is the owner
        self.checkOwnsList(objects)

        try:
            assert (heir[0].is_active == True), "User "+user.username+" is NOT active and therefore cannot become the new owner of the objects in the list."
        except AssertionError as error:
            print(error)
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print("The operation of '"+caller[1][3]+"' should not proceed")

        cargo = {}
        cargo["object_type"] = objects[0]._meta.model.__name__
        ids = []
        for obj in objects:
            ids.append(obj.id)
        cargo["object_ids"] = ids
        cargo["comment"] = justification
        mytask = ConfirmationTask.create_task(self,heir,'CedeOwnership',cargo)
        return mytask

    ####################################################################
    # Below this point lets put actions relevant only to the admin users

    def getAdmin():
        return Users.objects.filter(is_staff=True)

    # def deactivateUser(self,user):
    #     # See django documentation for is_active for login and permissions
    #     if self.is_staff and user.is_active:
    #         user.is_active = False
    #         user.save()

    # def activateUser(self,user):
    #     # See django documentation for is_active for login and permissions
    #     if self.is_staff and not user.is_active:
    #         user.is_active = True
    #         user.save()


class AbstractModelMeta(abc.ABCMeta,type(models.Model)):
    pass
    
class SingleObject(models.Model,metaclass=AbstractModelMeta):
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
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class AccessLevel(models.TextChoices):
        PUBLIC = "PUB"
        PRIVATE = "PRI"
    access_level = CharField(max_length=3,choices=AccessLevel.choices,default=AccessLevel.PUBLIC,help_text="Set public or private access to this object.")

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

    def getCreatedAt(self):
        """
        Return:
           datetime: A formatted datetime string of the `created_at` attribute.
        """
        return self.created_at

    def getModifiedAt(self):
        """
        Return:
           datetime: A formatted datetime string of the `modified_at` attribute.
        """
        return self.modified_at

    def getUsersWithAccess(self,user):
        """
        Checks which users have view access the the object.
        
        Args:
            `User`: a user that has to be the owner of the object.

        Return:
            queryset(`Users`): a queryset with all the users that have view access to the object. An empty queryset if none.
        """
        try:
            assert (user==self.owner),"The calling user is not the owner of the object."
        except AssertionError as error:
            print(error)
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print("The operation of '"+caller[1][3]+"' should not proceed")
        else:
            if self.access_level == 'PUB':
                #"Object is already public, no point to fetch users with access to it."
                return Users.objects.none()
            else:
                perm = "view_"+self._meta.db_table
                users = get_users_with_perms(self,with_group_users=False,only_with_perms_in=[perm])
                if users:
                    return users.exclude(username=self.owner.username).order_by('username') # exclude the owner
                else:
                    return Users.objects.none()

    def getGroupsWithAccess(self,user):
        """
        Checks which groups have view access the the object.

        Args:
            `User`: a user that has to be the owner of the object.

        Return:
            queryset(`Groups`): a queryset with all the groups that have view access to the object. An empty queryset if none.
        """
        try:
            assert (user==self.owner),"The calling user is not the owner of the object."
        except AssertionError as error:
            print(error)
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print("The operation of '"+caller[1][3]+"' should not proceed")
        else:
            if self.access_level == 'PUB':
                #"Object is already public, no point to fetch groups with access to it."
                return SledGroups.objects.none()
            else:
                groups = get_groups_with_perms(self).order_by('name')
                if groups:
                    return groups
                else:
                    return SledGroups.objects.none()
        
        
    
    # def getOwnerInfo():

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
    
    def __str__(self):
        return self.name

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
        # Attention: all this should result to no hits to the DB because it is supposed to work with querysets only...to check!
        lenses_public  = super().get_queryset().filter(access_level='PUB')
        lenses_private = super().get_queryset().filter(access_level='PRI')
        accessible_private_lenses = get_objects_for_user(user,'view_lenses',klass = lenses_private)
        return lenses_public | accessible_private_lenses # merge and return querysets

    def in_ids(self,user,id_list):
        lenses_public  = super().get_queryset().filter(access_level='PUB').filter(id__in=id_list)
        lenses_private = super().get_queryset().filter(access_level='PRI').filter(id__in=id_list)
        accessible_private_lenses = get_objects_for_user(user,'view_lenses',klass = lenses_private)
        return lenses_public | accessible_private_lenses # merge and return querysets

    
class ProximateLensManager(models.Manager):
    """
    Attributes:
        check_radius (`float`): A radius in arcsec, representing an area around each existing lens.
    """
    check_radius = 16 # in arcsec
    
    def get_DB_neighbours(self,lens):
        '''
        The custom SLED model for a group of users, inheriting from the django `Group`.

        Attributes:
            user (`User`): the user for whom to query the database for all the accessible lenses.
            

        Returns:
            neighbours (list `Lenses`): Returns which of the existing lenses in the database are within a 'radius' from the lens.
        '''
        qset = super().get_queryset().filter(access_level='PUB').annotate(distance=Func(F('ra'),F('dec'),lens.ra,lens.dec,function='distance_on_sky',output_field=FloatField())).filter(distance__lt=self.check_radius)
        if qset.count() > 0:
            return qset
        else:
            return False
        
    def get_DB_neighbours_many(self,lenses):
        index_list = []
        neis_list = [] # A list of non-empty querysets
        for i,lens in enumerate(lenses):
            neis = self.get_DB_neighbours(lens)
            if neis:
                index_list.append(i)
                neis_list.append(neis)
        return index_list,neis_list
    
    
    
class Lenses(SingleObject):    
    ra = models.DecimalField(max_digits=7,
                             decimal_places=4,
                             verbose_name="RA",
                             help_text="The RA of the lens [degrees].",
                             validators=[MinValueValidator(0.0,"RA must be positive."),
                                         MaxValueValidator(360,"RA must be less than 360 degrees.")])
    dec = models.DecimalField(max_digits=6,
                              decimal_places=4,
                              verbose_name="DEC",
                              help_text="The DEC of the lens [degrees].",
                              validators=[MinValueValidator(-90,"DEC must be above -90 degrees."),
                                          MaxValueValidator(90,"DEC must be below 90 degrees.")])
    name = models.CharField(blank=True,
                            max_length=100,
                            help_text="An identification for the lens, e.g. the usual phone numbers.")
    # alt_name = models.CharField(max_length=100,
    #                             help_text="A colloquial name with which the lens is know, e.g. 'The Einstein cross', etc.")  # This could become a comma separated list of names.
    #discovered_at = models.DateField(help_text="The date when the lens was discovered, or the discovery paper published.")
    flag_confirmed = models.BooleanField(default=False,
                                         blank=True,
                                         verbose_name="Confirmed",
                                         help_text="Set to true if the lens has been confirmed by a publication.")
    flag_contaminant = models.BooleanField(default=False,
                                           blank=True,
                                           verbose_name="Contaminant",
                                           help_text="Set to true if the object has been confirmed as NOT a lens by a publication.")
    image_sep = models.DecimalField(blank=True,
                                    null=True,
                                    max_digits=4,
                                    decimal_places=2,
                                    verbose_name="Separation",
                                    help_text="An estimate of the maximum image separation or arc radius [arcsec].",
                                    validators=[MinValueValidator(0.0,"Separation must be positive."),
                                                MaxValueValidator(10,"Separation must be less than 10 arcsec.")])
    z_source = models.DecimalField(blank=True,
                                   null=True,
                                   max_digits=4,
                                   decimal_places=3,
                                   verbose_name="Z source",
                                   help_text="The redshift of the source, if known.",
                                   validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                               MaxValueValidator(15,"If your source is further than that then congrats! (but probably it's a mistake)")])
    z_lens = models.DecimalField(blank=True,
                                 null=True,
                                 max_digits=4,
                                 decimal_places=3,
                                 verbose_name="Z lens",
                                 help_text="The redshift of the lens, if known.",
                                 validators=[MinValueValidator(0.0,"Redshift must be positive"),
                                             MaxValueValidator(15,"If your lens is further than that then congrats! (but probably it's a mistake)")])

    n_img = models.IntegerField(blank=True,
                                 null=True,
                                 verbose_name="Number of images",
                                 help_text="The number of source images, if known.",
                                 validators=[MinValueValidator(2,"For this to be a lens candidate, it must have at least 2 images of the source"),
                                             MaxValueValidator(15,"Wow, that's a lot of images, are you sure?")])

    info = models.TextField(blank=True,
                            default='',
                            help_text="Description of any important aspects of this system, e.g. discovery/interesting features/multiple discoverers/etc.")

    ImageConfChoices = (
        ('CUSP','Cusp'),
        ('FOLD','Fold'),
        ('CROSS','Cross'),
        ('DOUBLE','Double'),
        ('QUAD','Quad'),
        ('RING','Ring'),
        ('ARCS','Arcs')
    )
    image_conf = CharField(max_length=100,
                           blank=True,
                           null=True,
                           choices=ImageConfChoices,
                           verbose_name="Configuration")
    
    LensTypeChoices = (
        ('GALAXY','Galaxy'),
        ('GROUP','Group of galaxies'),
        ('CLUSTER','Galaxy cluster'),
        ('QUASAR','Quasar')
    )
    lens_type = CharField(max_length=100,
                          blank=True,
                          null=True,
                          choices=LensTypeChoices)
    
    SourceTypeChoices = (
        ('GALAXY','Galaxy'),
        ('QUASAR','Quasar'),
        ('GW','Gravitational Wave'),
        ('FRB','Fast Radio Burst'),
        ('GRB','Gamma Ray Burst'),
        ('SN','Supernova')
    )
    source_type = CharField(max_length=100,
                            blank=True,
                            null=True,
                            choices=SourceTypeChoices)

    
    accessible_objects = AccessibleLensManager() # the first manager is the default one
    proximate = ProximateLensManager()
    objects = models.Manager()
    
    class Meta():
        db_table = "lenses"
        ordering = ["ra"]
        #unique_together = ["ra","dec"] # removed because it causes invalid forms when updating
        constraints = [
            # Reiterate the validators
            # z_lens must be > lens_source
        ]
        verbose_name = "lens"
        verbose_name_plural = "lenses"

    def clean(self):
        if self.flag_confirmed and self.flag_contaminant:
            raise ValidationError('The object cannot be both a lens and a contaminant.')
        if self.flag_contaminant and (image_conf or lens_type or source_type):
            raise ValidationError('The object cannot be a contaminant and have a lens or source type, or an image configuration.')
        if self.z_lens and self.z_source:
            if self.z_lens > self.z_source:
                raise ValidationError('The source redshift cannot be lower than the lens redshift.')
        
    def __str__(self):
        if self.name:
            return self.name
        else:
            c = SkyCoord(ra=self.ra*u.degree, dec=self.dec*u.degree, frame='icrs')
            return 'J'+c.to_string('hmsdms')

    def create_name(self):
        c = SkyCoord(ra=self.ra*u.degree, dec=self.dec*u.degree, frame='icrs')
        self.name = 'J'+c.to_string('hmsdms')
        
    def get_absolute_url(self):
        #return reverse('lenses:lens-detail',kwargs={'lens_name':self.name})
        return "bleedf"

    def get_DB_neighbours(self,radius):
        neighbours = list(Lenses.objects.filter(access_level='PUB').annotate(distance=Func(F('ra'),F('dec'),self.ra,self.dec,function='distance_on_sky',output_field=FloatField())).filter(distance__lt=radius))
        return neighbours

    @staticmethod
    def distance_on_sky(ra1,dec1,ra2,dec2):
        '''
        This is the same implementation of the distance between a points on a sphere and the lens as the function 'distance_on_sky' in the database.

        Attributes:
            ra1,dec1 (`float`): the ra and dec of a point on the sphere. If not given, then the lens coordinates are used.
            ra2,dec2 (`float`): the ra and dec of another point.

        Returns:
            distance (`float`): the distance between the lens and the given point in arcsec.
        '''
        dec1_rad = math.radians(dec1);
        dec2_rad = math.radians(dec2);
        Ddec = abs(dec1_rad - dec2_rad);
        Dra = abs(math.radians(ra1) - math.radians(ra2));
        a = math.pow(math.sin(Ddec/2.0),2) + math.cos(dec1_rad)*math.cos(dec2_rad)*math.pow(math.sin(Dra/2.0),2);
        d = math.degrees( 2.0*math.atan2(math.sqrt(a),math.sqrt(1.0-a)) )
        return d*3600.0


            
        

################################################################################################################################################
### BEGIN: Confirmation task specific code
class ConfirmationTaskManager(models.Manager):
    def pending_for_user(self,user):
        return super().get_queryset().filter(status='P').filter(Q(owner=user)|Q(recipients__username=user.username))

    def all_for_user(self,user):
        return super().get_queryset().filter(Q(owner=user)|Q(recipients__username=user.username))

class ConfirmationTask(SingleObject):
    """
    The Confirmation task object.

    Attributes:
        task_name (str): the name of the task to perform.
        status (`enum`): completed if all the users have responded, otherwise pending.
        cargo (json): a JSON object that carries information necessary to complete the task once all responses have been received.
        recipients (`QuerySet`): A set of Users.

    Todo:
        - Associate the task name to a class (classes of confirmation task types will need to be implemented first). 
    """

    # The task types MUST match 1-to-1 the proxy models below
    class TaskType(models.TextChoices):
        CedeOwnership = 'CedeOwnership', _('Cede ownership')
        MakePrivate = 'MakePrivate', _('Make private')
        DeleteObject = 'DeleteObject', _('Delete public object')
    task_type = models.CharField(max_length=100,
                                 choices=TaskType.choices,
                                 help_text="The name of the task to perform.") 
    class StatusType(models.TextChoices):
        Pending = "P", _('Pending')
        Completed = "C", _('Completed')
    status = CharField(max_length=1,
                       choices=StatusType.choices,
                       default=StatusType.Pending,
                       help_text="Status of the task: 'Pending' (P) or 'Completed' (C).")
    cargo = models.JSONField(help_text="A json object holding any variables that will be executed upon completion of the task.")
    recipients = models.ManyToManyField(
        Users,
        related_name='confirmation_tasks',
        through='ConfirmationResponse',
        through_fields=('confirmation_task','recipient'),
        help_text="A many-to-many relationship between ConfirmationTask and Users that will need to respond."
    )
    recipient_names = []

    custom_manager = ConfirmationTaskManager()
    objects = models.Manager()
    
    def __str__(self):
        return '%s_$s' % (self.task_type,self.id)

    def get_absolute_url(self):
        return reverse('confirmation:single_task',kwargs={'task_id':self.id})

    class Meta():
        db_table = "confirmation_tasks"
        verbose_name = "confirmation_task"
        verbose_name_plural = "confirmation_tasks"

    def __init__(self, *args, **kwargs):
        super(ConfirmationTask,self).__init__(*args, **kwargs)
        subclass_found = False
        for _class in ConfirmationTask.__subclasses__():
            if self.task_type == _class.__name__:
                self.__class__ = _class
                subclass_found = True
                break
        if not subclass_found:
            raise ValueError(task_type)

    def create_task(sender,users,task_type,cargo):
        """
        Creates a task and assigns the recipients (list of users) to it via a many-to-many relation.

        It also invites the recipients by sending them a link via email.

        Args:
            sender (`User`): An instance of a `User` object.
            users (`QuerySet`): A queryset of User objects.
            task_type (str): The name of the task to perform once all users have responded.
            cargo (JSON): a JSON object with information required to complete the task.

        Returns:
            bool: True if the given user is the owner, False otherwise.
        """
        task = ConfirmationTask(owner=sender,task_type=task_type,cargo=cargo)
        task.save()
        task.recipients.set(users)
        task.save()
        task.recipient_names = list(users.values_list('username',flat=True))
        task.inviteRecipients(task.recipients)
        return task

    def load_task(task_id):
        """
        Loads a task based on the given id.

        If the task exists it returns it and sets the recipient_names variables, otherwise it returns None.

        Args:
            task_id (int): An integer representing the task id.

        Returns:
            ConfirmationTask object: if successful, otherwise None.
        """
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
            task.recipient_names = list(task.recipients.values_list('username',flat=True))
        except ConfirmationTask.DoesNotExist:
            task = None
        return task

    def inviteRecipients(self,users):
        """
        Emails list of recipients to inform/remind them that a confirmation task requires their response

        Args:
            recipients (`QuerySet`): A queryset of User objects.
        """
        site = Site.objects.get_current()
        subject = 'A %s task requires your response' % self.task_type
        message = 'Dear %s user, there is a %s task that requires your response. Click here for details: %s/confirmation/single/%s' % (site.name,self.task_type,site.domain,self.id)
        recipient_emails = list(users.values_list('email',flat=True))
        from_email = 'manager@%s' % site.domain
        #send_mail(subject,message,from_email,recipient_emails)
        
    def get_all_recipients(self):
        """
        Gets all the recipients of the confirmation task. 
         
        Returns:
            A QuerySet with User objects.
        """
        return self.recipients.all()

    def not_heard_from(self):
         """
         Checks which recipients have not responded yet. 
         
         Returns:
             A QuerySet with ConfirmationResponse objects.
         """
         return self.recipients.through.objects.filter(confirmation_task__exact=self.id,response__exact='')

    def heard_from(self):
         """
         Checks which recipients have already responded. 
         
         Returns:
             A QuerySet with ConfirmationResponse objects.
         """
         return self.recipients.through.objects.filter(confirmation_task__exact=self.id).exclude(response__exact='')

    def registerResponse(self,user,response,comment):
        """
        Registers the given users response to the confirmation task
        """
        if user.username not in self.recipient_names:
            raise ValueError(self.recipient_names,user.username) # Need custom exception here
        if response not in self.allowed_responses(): 
            raise ValueError(response) # Need custom exception here
        self.recipients.through.objects.filter(confirmation_task=self,recipient=user).update(response=response,response_comment=comment,created_at=timezone.now())
        

    def registerAndCheck(self,user,response,comment):
        """
        Registers the given recipients response and checks if all recipients have replied. If yes, calls finalizeTask and updates the status to completed.
        """
        self.registerResponse(user,response,comment)
        nhf = self.not_heard_from()
        if nhf.count() == 0:
            self.finalizeTask()
            self.status = self.StatusType.Completed
            self.save()

    # To be overwritten by the proxy models
    #@property
    #@abc.abstractmethod
    def allowed_responses(self):
        pass

    # To be overwritten by the proxy models
    #@abc.abstractmethod
    def finalizeTask(self):
        pass

    # To be overwritten by the proxy models
    #@abc.abstractmethod
    def getForm(self):
        pass
        
     
class ConfirmationResponse(models.Model):
    confirmation_task = models.ForeignKey(ConfirmationTask, on_delete=models.CASCADE)
    recipient = models.ForeignKey(Users,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    response = models.CharField(max_length=100, help_text="The response of a given user to a given confirmation task.") 
    response_comment = models.CharField(max_length=100, help_text="A comment (optional) from the recipient on the given response.") 

class DeleteObject(ConfirmationTask):
    class Meta:
        proxy = True
        
    class myForm(forms.Form):
        mychoices = [('yes','Yes'),('no','No')]
        response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
        response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

    def allowed_responses(self):
        return ['yes','no']

    def getForm(self):
        return self.myForm()

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        admin = Users.getAdmin().first()
        if response == 'yes':
            #cargo = json.loads(self.cargo)
            getattr(lenses.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids']).delete()
            notify.send(sender=admin,recipient=self.owner,verb='Your request to delete public objects was accepted',level='success',timestamp=timezone.now(),note_type='DeleteObjects',task_id=self.id)
        else:
            notify.send(sender=admin,recipient=self.owner,verb='Your request to delete public objects was rejected',level='error',timestamp=timezone.now(),note_type='DeleteObjects',task_id=self.id)

            
class CedeOwnership(ConfirmationTask):
    class Meta:
        proxy = True

    class myForm(forms.Form):
        mychoices = [('yes','Yes'),('no','No')]
        response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
        response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

    def allowed_responses(self):
        return ['yes','no']

    def getForm(self):
        return self.myForm()

    def finalizeTask(self,**kwargs):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        if response == 'yes':
            heir = self.get_all_recipients()[0]
            #cargo = json.loads(self.cargo)
            objs = getattr(lenses.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            objs.update(owner=heir)
            pri = []
            for lens in objs:
                if lens.access_level == 'PRI':
                    pri.append(lens)
            if pri:
                assign_perm('view_lenses',heir,pri) # don't forget to assign view permission to the new owner for the private lenses
            notify.send(sender=heir,recipient=self.owner,verb='Your CedeOwnership request was accepted',level='success',timestamp=timezone.now(),note_type='CedeOwnership',task_id=self.id)
            notify.send(sender=heir,recipient=heir,verb='You have accepted a CedeOwnership request',level='success',timestamp=timezone.now(),note_type='CedeOwnership',task_id=self.id)
        else:
            notify.send(sender=heir,recipient=self.owner,verb='Your CedeOwnership request was rejected',level='error',timestamp=timezone.now(),note_type='CedeOwnership',task_id=self.id)

        
class MakePrivate(ConfirmationTask):
    class Meta:
        proxy = True
        
    class myForm(forms.Form):
        mychoices = [('yes','Yes'),('no','No')]
        response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
        response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

    def allowed_responses(self):
        return ['yes','no']

    def getForm(self):
        return self.myForm()

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        admin = Users.getAdmin().first()
        if response == 'yes':
            #cargo = json.loads(self.cargo)
            getattr(lenses.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids']).update(access_level='PRI')
            notify.send(sender=admin,recipient=self.owner,verb='Your request to make objects private was accepted',level='success',timestamp=timezone.now(),note_type='MakePrivate',task_id=self.id)
        else:
            notify.send(sender=admin,recipient=self.owner,verb='Your request to make objects private was rejected',level='error',timestamp=timezone.now(),note_type='MakePrivate',task_id=self.id)
        


### END: Confirmation task specific code
################################################################################################################################################
