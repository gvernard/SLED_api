from django.db import models
from django.db.models import Q, F, CheckConstraint
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib.auth.models import Group

from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_user, get_users_with_perms, get_groups_with_perms

import abc
import inspect
import datetime
import pytz
from operator import itemgetter
from itertools import groupby


class Base:
    subs = ['Users']  # Ordered list of subclass names.

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        while cls.__name__ in cls.subs:
            cls.subs[cls.subs.index(cls.__name__)] = cls

class Users(Base):
    def objects(self):
        none = 3






class AccessManager(models.Manager):
    def all(self,user):
        """
        The main way to query the database by returning all public and those private objects for which the user has access.

        Args:
            user (`User`): A user instance.
        
        Returns:
            qset: A queryset with all the SingleObjects that this user can access.
        """
        # Attention: all this should result to no hits to the DB because it is supposed to work with querysets only...to check!
        public  = super().get_queryset().filter(access_level='PUB')
        private = super().get_queryset().filter(access_level='PRI')
        perm = 'view_'+self.model._meta.db_table
        accessible_private = get_objects_for_user(user,perm,klass = private)
        qset = public | accessible_private # merge querysets
        return qset

    def in_ids(self,user,id_list):
        """
        Same as the all() above, but the objects must be in the provided list of ids.

        Args:
            user (`User`): A user instance.
            id_list (List[int]): A list of ids of primary objects.

        Returns:
            qset: A queryset with all the SingleObjects that are in the list of ids and this user can access.
        """
        public  = super().get_queryset().filter(access_level='PUB').filter(id__in=id_list)
        private = super().get_queryset().filter(access_level='PRI').filter(id__in=id_list)
        perm = 'view_'+self.model._meta.db_table        
        accessible_private = get_objects_for_user(user,perm,klass = private)
        return public | accessible_private # merge and return querysets

    def owned(self,user):
        qset = super().get_queryset().filter(owner=user)
        return qset

    def _arrange_by_object(self,ugs_objects_pairs,ugs,objects):
        """
        Takes a list of tuples matching a User/Group to an object and returns the Users/Groups per object.

        Args:
            ugs_objects_pairs (List[tuples(ug,object)]): This is a list of tuples, with each tuple containing the index of a User/Group in the ugs list and the index of the object.
            ugs (List[`Users` and/or `Group`]): A list of User and/or Group objects.
            objects (List[SingleObject]): A list of SingleObjects.

        Returns:
            out (List[dict]): A list of dictionaries, each containing an "object" and "ugs" keys. The "object" contains only one object and the "ugs" a list of User and Group objects.
        """
        object_ugs = {key: list(map(itemgetter(0), ele)) for key, ele in groupby(sorted(ugs_objects_pairs,key=itemgetter(1)), key = itemgetter(1))}
        out = []
        for key in object_ugs:
            tmp_dict = {"object": objects[key]}
            tmp_list = []
            for i in object_ugs[key]:
                tmp_list.append(ugs[i])
            tmp_dict["ugs"] = tmp_list
            out.append(tmp_dict)
        return out
    
    def without_access(self,ugs,objects):
        """
        Cross matches the given Users or Group with the given objects and returns those users or groups that do NOT have access to the objects.

        Args:
            ugs [List(User or Group)]: A list of Users and or Group.
            objects [List(SingleObject)]: A list of SingleObjects. Public objects are ignored.

        Returns:
            object_ugs (List[dict]): The output of '_arrange_by_object' - a list of dictionaries, each containing an "object" and "ugs" keys. The "object" contains only one object and the "ugs" a list of User and Group objects.
        """
        perm = "view_"+objects[0]._meta.db_table
        pairs = []
        for j,ug in enumerate(ugs):
            checker = ObjectPermissionChecker(ug)
            checker.prefetch_perms(objects)
            for i,obj in enumerate(objects):
                if obj.access_level == 'PRI' and not checker.has_perm(perm,obj):
                    pairs.append((j,i))
        out = self._arrange_by_object(pairs,ugs,objects)
        return out

    def with_access(self,ugs,objects):
        """
        Cross matches the given Users or Group with the given objects and returns those users or groups that DO have access to the objects.

        Args:
            ugs [List(User or Group)]: A list of Users or Group but not both.
            objects [List(SingleObject)]: A list of SingleObjects. Public objects are ignored.

        Returns:
            object_ugs (List[dict]): The output of '_arrange_by_object' - a list of dictionaries, each containing an "object" and "ugs" keys. The "object" contains only one object and the "ugs" a list of User and Group objects.
        """
        perm = "view_"+objects[0]._meta.db_table
        pairs = []
        for j,ug in enumerate(ugs):
            checker = ObjectPermissionChecker(ug)
            checker.prefetch_perms(objects)
            for i,obj in enumerate(objects):
                if obj.access_level == 'PRI' and checker.has_perm(perm,obj):
                    pairs.append((j,i))
        out = self._arrange_by_object(pairs,ugs,objects)
        return out

    
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
    """
    
    owner = models.ForeignKey('Users',on_delete=models.CASCADE) 
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    class AccessLevel(models.TextChoices):
        PUBLIC = "PUB"
        PRIVATE = "PRI"
    access_level = models.CharField(max_length=3,choices=AccessLevel.choices,default=AccessLevel.PUBLIC,help_text="Set public or private access to this object.")

    accessible_objects = AccessManager()
    objects = models.Manager()


    class Meta():
        abstract = True
        get_latest_by = ["modified_at","created_at"]
        constraints = [
            #CheckConstraint(check=Q(created_at__gt=pytz.utc.localize(datetime.datetime(2021,11,11))),name='created_recently'),
            CheckConstraint(check=Q(modified_at__gt=F('created_at')),name='%(class)s_modified_after_created')
        ]

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
        
    def assertOwner(self,user):
        """
        Same as isOwner above, but it performs an assertion.
        """
        try:
            assert (user==self.owner),"The calling user is not the owner of the object."
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
        
    def convertToList(self,objects):
        """
        Checks if the provided objects are a list or a single instance. If the latter, then converts it to a list (with just one object in it).

        Args:
            objects: A list or an instance of a SingleObject.

        Returns:
            objects: A list of objects.
        """
        if isinstance(objects,SingleObject):
            objects = [objects]
        return objects
        
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
        self.assertOwner(user)
        return self.getUsersWithAccessNoOwner()

    def getUsersWithAccessNoOwner(self):
        if self.access_level == 'PUB':
            #"Object is already public, no point to fetch users with access to it."
            return []
        else:
            perm = "view_"+self._meta.db_table
            users = get_users_with_perms(self,with_group_users=False,only_with_perms_in=[perm])
            if users:
                return list(users.exclude(username=self.owner.username).order_by('username')) # exclude the owner
            else:
                return []

    def getGroupsWithAccess(self,user):
        """
        Checks which groups have view access the the object.

        Args:
            `User`: a user that has to be the owner of the object.

        Return:
            queryset(`Groups`): a queryset with all the groups that have view access to the object. An empty queryset if none.
        """
        self.assertOwner(user)
        return self.getGroupsWithAccessNoOwner()

    def getGroupsWithAccessNoOwner(self):
        if self.access_level == 'PUB':
            #"Object is already public, no point to fetch groups with access to it."
            return []
        else:
            groups = get_groups_with_perms(self)
            if groups:
                # # this trick is required to convert Group (used by django guardian) to SledGroup
                # ids = []
                # for group in groups:
                #     ids.append(group.id)
                # return list(Group.objects.filter(id__in=ids))
                return list(groups)
            else:
                return []
