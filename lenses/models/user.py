from django.db import models
from django.db.models import Q, CharField, Count
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
from django.apps import apps

from guardian.core import ObjectPermissionChecker
from guardian.mixins import GuardianUserMixin
from guardian.shortcuts import assign_perm, remove_perm, get_objects_for_group, get_objects_for_user

from notifications.signals import notify
from actstream import action
from actstream.actions import unfollow

from operator import itemgetter
from itertools import groupby
import inspect

from . import SledGroup, SingleObject, ConfirmationTask, Collection, AdminCollection
from mysite.language_check import validate_language

# Dummy array containing the primary objects in the database. Should be called from a module named 'constants.py' or similar.
objects_with_owner = ["Lenses","ConfirmationTask","Collection","Imaging","Spectrum","Catalogue","Redshift","GenericImage","LensModels"]#,"Finders","Scores","ModelMethods"]



'''
from django.db.models import Aggregate

class MyConcat(Aggregate):
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'
    
    def __init__(self, expression, distinct=False, **extra):
        print(expression)
        print(extra)
        super(MyConcat, self).__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            output_field=CharField(),
            **extra)
'''





class Users(AbstractUser,GuardianUserMixin):
    """ The class to represent registered users within SLED.

    A SLED user can own objects with which they can interact, e.g. give access to other users, cede ownership, add/remove objects from owned collections, etc.

    SLED users can also be added into groups, none or several, or be the owners of groups (of which they are members).
    
    Attributes:
        affiliation (`CharField`): Affiliation is the only field in addition to the standard django `User` fields. User groups (see ~SledGroups) are taken care of by the existing django modules.
    """
    email = models.EmailField(unique=True,
                              blank=False)
    affiliation = models.CharField(
        blank=False,
        max_length=100,
        help_text="An affiliation, e.g. an academic or research institution etc.")
    homepage = models.URLField(
        blank=True,
        max_length=200,
        help_text="A link to your homepage.")
    info = models.TextField(
        blank=False,
        default='',
        help_text="A short description of your work and interests.",
        validators=[validate_language])
    avatar = models.URLField(
        blank=True,
        max_length=300)
    slack_display_name = models.CharField(
        blank=True,
        max_length=100,
        help_text="Your 'Display Name' in the SLED Slack workspace.")
    
    class Meta():
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["username"]
    
    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('sled_users:user-visit-card',kwargs={'username':self.username})

    
    def getOwnedObjects(self,user_object_types=None):
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

    
    def leaveGroup(self,group):
        if self != group.owner:
            if self in group.getAllMembers(): 
                group.user_set.remove(self)
                action.send(self,target=group,verb='LeftGroup',level='error',user_name=self.username,user_url=self.get_absolute_url())
                

    def getGroupsIsMember(self):
        """
        Provides access to all the Groups that the user is a member of.

        Returns:
            A QuerySet to match the groups the user is a member of.
        """
        user = Users.objects.get(username=self.username)
        groups = SledGroup.objects.filter(user=user)
        return groups

    
    def getGroupsIsMemberNotOwner(self):
        """
        Provides access to all the Groups that the user is a member of but not the owner.

        Returns:
            A QuerySet to match the groups the user is a member of but not the owner.
        """
        user = Users.objects.get(username=self.username)
        groups = SledGroup.objects.filter(user=user).filter(~Q(owner=user))
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

        # Get the list of objects as a queryset
        object_type = objects[0]._meta.model.__name__
        model_ref = apps.get_model(app_label="lenses",model_name=object_type)
        objects_qset = model_ref.objects.filter(id__in=[obj.id for obj in objects])
        
        # User owns all objects, proceed with giving access
        perm = "view_"+objects[0]._meta.model_name

        # first loop over the target_users
        set1 = set(objects)
        for user in target_users:
            new_objects_per_user = []
            # if there are objects for which this user was just granted new permission, create a notification
            if isinstance(user,SledGroup):
                set2 = set(get_objects_for_group(user,perm,klass=objects_qset))
            else:
                set2 = set(get_objects_for_user(user,perm,klass=objects_qset,use_groups=False))
            new_objects_per_user = list(set1.difference(set2))
            if len(new_objects_per_user) > 0:
                # Below I have to loop over each object individually because of the way assign_perm is coded.
                # If the given obj is a list, the it calls bulk_assign_perms that checks for any permission (including through a group) using ObjectPermissionChecker.
                # As a result, if a user already has access through a group explicit permission (user-object pair) is not created.
                for obj in new_objects_per_user:
                    assign_perm(perm,user,obj)
                
                ad_col = AdminCollection.objects.create(item_type=object_type,myitems=new_objects_per_user)
                if isinstance(user,Users):
                    notify.send(sender=self,
                                recipient=user,
                                verb='GiveAccessNote',
                                level='success',
                                timestamp=timezone.now(),
                                action_object=ad_col)
                else:
                    action.send(self,target=user,verb='GiveAccessGroup',level='success',action_object=ad_col) # the user here is a group

                    
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
        perm = "view_"+objects[0]._meta.model_name

        # Loop over the target_users
        for user in target_users:
            # fetch permissions for all the objects for the given user (just 1 query)
            checker = ObjectPermissionChecker(user) # ObjectPermissionChecker here is fine because we are revoking access
            checker.prefetch_perms(objects)            
            object_type = objects[0]._meta.model.__name__
            model_ref = apps.get_model(app_label="lenses",model_name=object_type)
            revoked_objects_per_user = []
            for obj in objects:
                if checker.has_perm(perm,obj):
                    revoked_objects_per_user.append(obj)
            # if there are objects for which this user had permissions just revoked, create a notification
            if len(revoked_objects_per_user) > 0:
                ad_col = AdminCollection.objects.create(item_type=object_type,myitems=revoked_objects_per_user)
                if isinstance(user,Users):
                    notify.send(sender=self,
                                recipient=user,
                                verb='RevokeAccessNote',
                                level='error',
                                timestamp=timezone.now(),
                                action_object=ad_col)
                    for obj in revoked_objects_per_user:
                        unfollow(user,obj)
                else:
                    action.send(self,target=user,verb='RevokeAccessGroup',level='error',action_object=ad_col)  # here the user is actually a group

                qset = model_ref.objects.filter(id__in=[obj.id for obj in revoked_objects_per_user])
                if object_type not in ['Collection','Imaging','Spectrum','Catalogue']:
                    # Check collections: every collection owner must have access to all the objects in the collection.
                    # So, if access from user was revoked, check if they own a collection that contains the object and remove it from there.
                    self.remove_from_third_collections(qset,user)

                # Finally remove the permissions    
                remove_perm(perm,user,qset) # (just 1 query)
            
                    
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
            output = {'success':False,'message':"All objects are already public!",'duplicates':[]}
            return output
        else:
            object_type = target_objs.model.__name__
            model_ref = apps.get_model(app_label='lenses',model_name=object_type)
            perm = "view_"+object_type.lower()
            target_objs = list(target_objs)
                        
            ### Per user
            #####################################################            
            users_with_access,accessible_objects = self.accessible_per_other(target_objs,'users')
            for i,user in enumerate(users_with_access):
                object_ids = []
                for j in accessible_objects[i]:
                    object_ids.append(target_objs[j].id)
                qset = model_ref.accessible_objects.in_ids(user,object_ids)
                remove_perm(perm,user,qset) # Remove all the view permissions for these objects that are to be updated (just 1 query)
                ad_col = AdminCollection.objects.create(item_type=object_type,myitems=qset)
                notify.send(sender=self,
                            recipient=user,
                            verb='MakePublicNote',
                            level='info',
                            timestamp=timezone.now(),
                            action_object=ad_col)

            ### Per group
            #####################################################
            groups_with_access,accessible_objects = self.accessible_per_other(target_objs,'groups')
            id_list = [g.id for g in groups_with_access]
            gwa = SledGroup.objects.filter(id__in=id_list) # Needed to cast Group to SledGroup
            for i,group in enumerate(groups_with_access):
                object_ids = []
                for j in accessible_objects[i]:
                    object_ids.append(target_objs[j].id)
                qset = model_ref.objects.filter(pk__in=object_ids)
                ad_col = AdminCollection.objects.create(item_type=object_type,myitems=qset) # I have to create the ad_col with this queryset
                qset = get_objects_for_group(group,perm,qset)
                remove_perm(perm,group,qset) # Remove all the view permissions for these objects that are to be updated (just 1 query)
                action.send(self,target=gwa[i],verb='MadePublicGroup',level='info',action_object=ad_col)

            # Finally, update only those objects that need to be updated
            #####################################################
            for obj in target_objs:
                obj.access_level = 'PUB'
                obj.save()

            ad_col = AdminCollection.objects.create(item_type=object_type,myitems=target_objs)
            action.send(self,target=Users.getAdmin().first(),verb='MadePublicHome',level='info',action_object=ad_col)
            
            output = {'success':True,'message': '<b>%d</b> private %s are know public.' % (len(target_objs),object_type),'duplicates':[]}
            return output

        
    def makePrivate(self,qset,justification=None):
        """
        Changes the AccessLevel of the given objects to 'private'.
        
        First makes sure that the user owns all the objects, then creates a confirmation task for the database admin.

        Args:
            objects(queryset <SingleObject>): A queryset of primary objects of a specific type.

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
        cargo['user_admin'] = Users.selectRandomAdmin()[0].username

        if cargo["object_type"] == "Lenses":
            with_papers = qset.annotate(paper_count=Count('papers')).filter(paper_count__gt=0)
            try:
                assert (len(with_papers) == 0), "Lenses that are in papers cannot be made private!"
            except AssertionError as error:
                print(error)
                print("The following lenses are in papers: ")
                for lens in with_papers:
                    print(lens.__str__())
                caller = inspect.getouterframes(inspect.currentframe(),2)
                print("The operation of '"+caller[1][3]+"' should not proceed")
                raise
            else:
                mytask = ConfirmationTask.create_task(self,Users.getAdmin(),'MakePrivate',cargo)
                return mytask
        else:
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


    def get_collection_owners(self,objects):
        obj_ids = list(objects.values_list('id',flat=True))

        #cols = Collection.objects.filter(Q(item_type='Lenses') & Q(collection_myitems__gm2m_pk__in=obj_ids)).values_list('owner__username')
        #print(cols)
        
        object_type = objects.model.__name__
        users = Users.objects.filter(Q(collection__item_type=object_type) & Q(collection__collection_myitems__gm2m_pk__in=obj_ids))
        return users

        
    def remove_from_third_collections(self,objects,user):
        user_type = user._meta.model.__name__
        if user_type != 'SledGroup':
            obj_ids = list(objects.values_list('id',flat=True))
            object_type = objects.model.__name__
            cols = Collection.accessible_objects.owned(user).filter(Q(item_type=object_type) & Q(collection_myitems__gm2m_pk__in=obj_ids))

            if len(cols) > 0:
                for col in cols:
                    to_remove = col.myitems.filter(gm2m_pk__in=obj_ids)
                    col.removeItems(user,to_remove)

                ad_col = AdminCollection.objects.create(item_type=cols.model.__name__,myitems=cols)
                notify.send(sender=self,
                            recipient=user,
                            verb='RemovedFromThirdCollectionNote',
                            level='error',
                            timestamp=timezone.now(),
                            action_object=ad_col,
                            object_type=object_type
                            )


    def get_pending_tasks(self):
        # This is to facilitate calls in templates
        pending_tasks = list(ConfirmationTask.custom_manager.pending_for_user(self))
        return pending_tasks


    def get_roles(self):
        roles = []
        if self.limitsandroles.is_inspector:
            roles.append('inspector') 
        if self.limitsandroles.is_admin:
            roles.append('admin') 
        if self.limitsandroles.is_super_admin:
            roles.append('super admin') 
        if len(roles) > 0:
            return ','.join(roles)
        else:
            return ''


    

    
    ####################################################################
    # Below this point lets put actions relevant only to the admin users
    def getAdmin():
        return Users.objects.filter(is_superuser=True) # This refers to the django user 'admin'
    

    def selectRandomAdmin(exclude_usernames=None):
        # Returns a queryset
        if exclude_usernames is None:
            exclude_usernames = []
        user_id = Users.objects.filter(limitsandroles__is_admin=True).exclude(username__in=exclude_usernames).order_by('?').first().id
        qset = Users.objects.filter(id=user_id)
        return qset

    
    def selectRandomInspector(exclude_usernames=None):
        # Returns a queryset
        if exclude_usernames is None:
            exclude_usernames = []
        user_id = Users.objects.filter(limitsandroles__is_inspector=True).exclude(username__in=exclude_usernames).order_by('?').first().id
        qset = Users.objects.filter(id=user_id)
        return qset

    
    def get_admin_pending_tasks(self):
        if self.limitsandroles.is_admin:
            admin = Users.getAdmin()[0]
            pending_tasks = list(ConfirmationTask.objects.filter(status='P').filter(Q(owner=admin)|Q(recipients__username=admin.username)))
            return pending_tasks
        else:
            return []

        
    def get_admin_notifications(self):
        if self.limitsandroles.is_admin:
            admin = Users.getAdmin()[0]
            return admin.notifications.unread()
        else:
            return []




    def check_all_limits(self,N,obj_type='all'):
        remaining = {
            "errors": []
        }
        #print(N,obj_type)
        N_remaining_owned = self.check_limit_owned(N,obj_type)
        if N_remaining_owned < 0:
            remaining["errors"].append('You have exceeded the limit of owned objects! Contact the admins.')
        else:
            remaining["N_remaining_owned"] = N_remaining_owned
        
        N_remaining_week = self.check_limit_add_week(N,obj_type)
        if N_remaining_week < 0:
            remaining["errors"].append('You have exceeded the weekly limit of adding objects! Wait for a max. of 7 days, or contact the admins.')
        else:
            remaining["N_remaining_week"] = N_remaining_week

        return remaining
    
        
    def check_limit_owned(self,N,obj_type='all'):
        owned_objects = self.getOwnedObjects()
        N_owned = 0
        for model_type,qset in owned_objects.items():
            N_owned = N_owned + qset.count()
        remaining = self.limitsandroles.limit_total_owned - N_owned - N
        return remaining

        
    def check_limit_add_week(self,N,obj_type='all'):
        owned_objects = self.getOwnedObjects()
        N_week = 0
        last_seven_days = timezone.now() - timezone.timedelta(days=7)
        for model_type,qset in owned_objects.items():
            N_week = N_week + qset.filter(created_at__gt=last_seven_days).count()
        remaining = self.limitsandroles.limit_add_per_week - N_week - N
        return remaining
        


        
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
