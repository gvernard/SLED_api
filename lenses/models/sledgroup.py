from django.utils import timezone
from django.db import models
from django.contrib.auth.models import Group
from django.urls import reverse

import simplejson as json

from . import SingleObject, AdminCollection

from notifications.signals import notify
from actstream import action
from dirtyfields import DirtyFieldsMixin

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

    
    class Meta():
        db_table = "sledgroups"
        verbose_name = "sledgroup"
        verbose_name_plural = "sledgroups"
        ordering = ["name"]
        # constrain on the Min and Max number of users that are members?

        
    def save(self,*args,**kwargs):
        dirty = self.get_dirty_fields(verbose=True)
        if len(dirty) > 0:
            action.send(self.owner,
                        target=self,
                        verb='UpdateSelf',
                        level='success',
                        object_type='SledGroup',
                        fields=json.dumps(dirty))

        # Call save first, to create a primary key
        super().save(*args,**kwargs)
        self.user_set.add(self.owner)

        
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
                            verb='AddedToGroup',
                            level='success',
                            timestamp=timezone.now(),
                            action_object=self)

            #to_add = sled_user_qset.values_list('username',flat=True)
            #action.send(owner,target=self,verb='AddedToGroup',level='info',user_names=[u.username for u in to_add],user_urls=[u.get_absolute_url() for u in to_add])
            ad_col = AdminCollection.objects.create(item_type="Users",myitems=sled_user_qset)
            action.send(owner,target=self,verb='AddedToGroup',level='info',action_object=ad_col)

            
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
                            verb='RemovedFromGroup',
                            level='error',
                            timestamp=timezone.now(),
                            action_object=self)

            #to_remove = sled_user_qset.values_list('username',flat=True)
            #action.send(owner,target=self,verb='RemovedFromGroup',level='info',user_names=[u.usernames for u in to_remove],user_urls=[u.get_absolute_url() for u in to_remove])
            ad_col = AdminCollection.objects.create(item_type="Users",myitems=sled_user_qset)
            action.send(owner,target=self,verb='RemovedFromGroup',level='info',action_object=ad_col)


    def delete(self, *args, **kwargs):
        # notify group members.
        members = self.getAllMembers()
        for member in members:
            notify.send(sender=self.owner,
                        recipient=member,
                        verb='DeletedGroup',
                        level='warning',
                        timestamp=timezone.now(),
                        group_name=self.name,
                        owner_name=self.owner.username,
                        owner_url=self.owner.get_absolute_url())

        super().delete(*args, **kwargs)  # Call the "real" delete() method.
