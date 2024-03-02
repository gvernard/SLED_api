from django.utils import timezone
from django.db import models
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.dispatch import receiver
from django.db.models.signals import pre_delete
from django.apps import apps

import simplejson as json
from guardian.shortcuts import get_objects_for_group,remove_perm,get_perms_for_model

from . import SingleObject, AdminCollection

from notifications.models import Notification
from notifications.signals import notify
from actstream import action
from actstream.models import target_stream
from dirtyfields import DirtyFieldsMixin

import inspect

objects_with_group_access = ["Lenses","Collection","Imaging","Spectrum","Catalogue","Redshift"]#,"Finders","Scores","ModelMethods","Models","FutureData","Data"]


class SledGroup(Group,SingleObject,DirtyFieldsMixin):
    """
    The custom SLED model for a group of users, inheriting from the django `Group`.

    Attributes:
        description(`str`): A short description of the group's purpose.

    Todo:
        - Should this be a SingleObject? If so then the access_level should always be set to public and we will not be using access related functions.
        - Related to the above, it doesn't make sense to have collections of groups, so no need to use the addToCollection, etc, functions.

    """
    description = models.CharField(max_length=200,null=True, blank=True)

    # Fields to report updates on
    FIELDS_TO_CHECK = ['name','description','owner','access_level']

    class Meta():
        db_table = "sledgroups"
        verbose_name = "Group"
        verbose_name_plural = "Groups"
        ordering = ["name"]
        # constrain on the Min and Max number of users that are members?

        
    def save(self,*args,**kwargs):
        if self._state.adding:
            super().save(*args,**kwargs)
            self.user_set.add(self.owner)
            self.save()
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

            if len(dirty) > 0:
                action.send(self.owner,target=self,verb='UpdateLog',level='info',fields=json.dumps(dirty))

            super().save(*args,**kwargs)

        
    def __str__(self):
        return self.name

    
    def get_absolute_url(self):
        return reverse('sled_groups:group-detail',kwargs={'pk':self.id})


    def getAllMembers(self):
        """
        Note:
            We may want to restrict this function to the owner, or to members only
        """
        users = self.user_set.all()
        return users

    
    def addMember(self,owner,sled_user_qset):
        try:
            assert (owner==self.owner), "User trying to add group members is not the owner of the group."
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise

        try:
            to_add = set(sled_user_qset.values_list('username',flat=True))
            members = set(self.getAllMembers().values_list('username',flat=True))
            assert (len(to_add.intersection(members)) == 0), "Users are already in the group"
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
        else:
            self.user_set.add(*sled_user_qset)
            for new_member in sled_user_qset:
                notify.send(sender=owner,
                            recipient=new_member,
                            verb='AddedToGroupNote',
                            level='success',
                            timestamp=timezone.now(),
                            action_object=self)

            #to_add = sled_user_qset.values_list('username',flat=True)
            #action.send(owner,target=self,verb='AddedToGroup',level='info',user_names=[u.username for u in to_add],user_urls=[u.get_absolute_url() for u in to_add])
            ad_col = AdminCollection.objects.create(item_type="Users",myitems=sled_user_qset)
            action.send(owner,target=self,verb='AddedToGroup',level='success',action_object=ad_col)

            
    def removeMember(self,owner,sled_user_qset):
        try:
            assert (owner==self.owner), "User trying to remove group members is not the owner of the group."
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise

        try:
            to_remove = set(sled_user_qset.values_list('username',flat=True))
            members = set(self.getAllMembers().values_list('username',flat=True))
            assert (to_remove.issubset(members)), "Users are not already in the group"
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
        else:
            self.user_set.remove(*sled_user_qset)
            for removed_member in sled_user_qset:
                notify.send(sender=owner,
                            recipient=removed_member,
                            verb='RemovedFromGroupNote',
                            level='error',
                            timestamp=timezone.now(),
                            action_object=self)

            #to_remove = sled_user_qset.values_list('username',flat=True)
            #action.send(owner,target=self,verb='RemovedFromGroup',level='info',user_names=[u.usernames for u in to_remove],user_urls=[u.get_absolute_url() for u in to_remove])
            ad_col = AdminCollection.objects.create(item_type="Users",myitems=sled_user_qset)
            action.send(owner,target=self,verb='RemovedFromGroup',level='error',action_object=ad_col)

    def getAccessibleObjects(self,object_types=None):
        if object_types == None:
            filtered_object_types = objects_with_group_access
        else:
            filtered_object_types = [x for x in object_types if x in objects_with_group_access]
        objects = {}
        for table in filtered_object_types:
            model_ref = apps.get_model(app_label='lenses',model_name=table)
            perm = 'view_'+table.lower()
            objects[model_ref._meta.verbose_name_plural.title()] = get_objects_for_group(self,perm,klass=model_ref)
        return objects


#@receiver(pre_delete,sender=SledGroup)
#def my_handler(sender, instance, **kwargs):
#    print('EDW')
