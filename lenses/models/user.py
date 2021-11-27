from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
from django.apps import apps

from guardian.core import ObjectPermissionChecker
from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import assign_perm, remove_perm

from notifications.signals import notify

from operator import itemgetter
from itertools import groupby
import inspect

from . import SledGroup
from . import SingleObject
from . import ConfirmationTask

# Dummy array containing the primary objects in the database. Should be called from a module named 'constants.py' or similar.
objects_with_owner = ["Lenses","ConfirmationTask","Collection"]#,"Finders","Scores","ModelMethods","Models","FutureData","Data"]


class Users(AbstractUser,GuardianUserMixin):
    """ The class to represent registered users within SLED.

    A SLED user can own objects with which they can interact, e.g. give access to other users, cede ownership, add/remove objects from owned collections, etc.

    SLED users can also be added into groups, none or several, or be the owners of groups (of which they are members).
    
    Attributes:
        affiliation (`CharField`): Affiliation is the only field in addition to the standard django `User` fields. User groups (see ~SledGroups) are taken care of by the existing django modules.
    """
    affiliation = models.CharField(max_length=100, help_text="An affiliation, e.g. an academic or research institution etc.")

    class Meta():
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["username"]
    
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
            model_ref = apps.get_model(app_label='lenses',model_name=table)
            objects[table] = model_ref.accessible_objects.owned(self)
        return objects

    def getGroupsIsMember(self):
        """
        Provides access to all the Groups that the user is a member of.

        Returns:
            A QuerySet to match the groups the user is a member of.
        """
        user = Users.objects.get(username=self.username)
        groups = SledGroup.objects.filter(user=user)
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
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
            
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
        if isinstance(target_users,Users) or isinstance(target_users,SledGroup):
            target_users = [target_users]
        if self in target_users:
            target_users.remove(self)
        # Check that user is the owner
        self.checkOwnsList(objects)

        # User owns all objects, proceed with giving access
        perm = "view_"+objects[0]._meta.db_table

        # first loop over the target_users
        for user in target_users:
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
            target_users(List[User or Group]): A list of User, or Group, or mixed.
        """
        # If input argument 'objects' is a single value, convert to list
        if isinstance(objects,SingleObject):
            objects = [objects]
        # Check that user is the owner
        self.checkOwnsList(objects)
        # If input argument 'target_users' is a single value, convert to list
        if isinstance(target_users,Users) or isinstance(target_users,SledGroup):
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
            model_ref = apps.get_model(app_label="lenses",model_name=object_type)
            revoked_objects_per_user_ids = []
            for obj in objects:
                if checker.has_perm(perm,obj):
                    revoked_objects_per_user_ids.append(obj.id)
            # if there are objects for which this user had permissions just revoked, create a notification
            if len(revoked_objects_per_user_ids) > 0:
                remove_perm(perm,user,model_ref.objects.filter(id__in=revoked_objects_per_user_ids)) # (just 1 query)
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
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
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
        
    def makePublic(self,qset):
        """
        Changes the access_level of the given objects to private.

        First makes sure that the user owns all the objects, then updates only those objects that are private with a single query to the database.

        Args:
            objects(queryset <SingleObject>): A queryset of primary objects of a specific type.

        Returns:
            A dictionary with the following entries:
            success (Bool): True if the operation was successful, False otherwise.
            message (str): A success or error message.
            duplicates (list[SingleObject]): A subset of the input objects, those that have close neighbours already existing in the database (possible duplicates)
        """
        # Check that user is the owner
        self.checkOwnsList(list(qset))

        # Loop over the list, act only on those objects that are private
        target_objs = qset.filter(access_level__exact='PRI')

        if target_objs.count() == 0:
            output = {'success':False,'message':"All objects are already public",'duplicates':[]}
            return output
        else:
            object_type = target_objs.model.__name__
            model_ref = apps.get_model(app_label='lenses',model_name=object_type)
            perm = "view_"+object_type
            target_objs = list(target_objs)
            
            ### Very important: check for proximity before making public.
            #####################################################            
            if object_type == 'Lenses':
                indices,neis = model_ref.proximate.get_DB_neighbours_many(target_objs)
                if indices:
                    # Possible duplicates, return them
                    to_check = [target_objs[i] for i in indices]
                    output = {'success':False,'message':'Existing public lenses too close - possible duplicates.','duplicates':to_check}
                    return output
            
            ### Per user
            #####################################################            
            users_with_access,accessible_objects = self.accessible_per_other(target_objs,'users')
            for i,user in enumerate(users_with_access):
                obj_ids = []
                for j in accessible_objects[i]:
                    obj_ids.append(target_objs[j].id)
                remove_perm(perm,user,model_ref.objects.filter(id__in=obj_ids)) # Remove all the view permissions for these objects that are to be updated (just 1 query)
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
            groups_with_access,accessible_objects = self.accessible_per_other(target_objs,'groups')
            for i,group in enumerate(groups_with_access):
                obj_ids = []
                for j in accessible_objects[i]:
                    obj_ids.append(target_objs[j].id)
                remove_perm(perm,group,model_ref.objects.filter(id__in=obj_ids)) # Remove all the view permissions for these objects that are to be updated (just 1 query)
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
            for obj in target_objs:
                obj.access_level = 'PUB'
            model_ref.objects.bulk_update(target_objs,['access_level'])

            output = {'success':True,'message': '<p>%d private %s are know public.</p>' % (len(target_objs),object_type),'duplicates':[]}
            return output
                
    def makePrivate(self,qset,justification=None):
        """
        Changes the AccessLevel of the given objects to 'private'.
        
        First makes sure that the user owns all the objects, then creates a confirmation task for the database admin.

        Args:
            objects(List[SingleObject]): A list of primary objects of a specific type.

        Returns:
            task: A confirmation task
        """
        # Check that user is the owner
        self.checkOwnsList(list(qset))

        cargo = {}
        cargo["object_type"] = qset.model.__name__
        ids = []
        for obj in qset:
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
            raise
        
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
