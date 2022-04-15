from django.utils import timezone
from django.db import models
from django.contrib.auth.models import Group
from django.urls import reverse

import simplejson as json

from . import SingleObject

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
                        verb="Fields have been updated",
                        level='success',
                        action_type='UpdateSelf',
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
                            verb='Your were successfully added to the group %s.' % self.name,
                            level='success',
                            timestamp=timezone.now(),
                            note_type='AddedToGroup')

            to_add = sled_user_qset.values_list('username',flat=True)
            if len(to_add) > 1:
                myverb = 'New users %s were added to the group.' % ','.join(to_add)
            else:
                myverb = 'New user %s was added to the group.' % to_add[0]
            action.send(owner,
                        target=self,
                        verb=myverb,
                        level='info',
                        action_type='AddedToGroup')


            
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
                            verb='Your were removed from the group %s.' % self.name,
                            level='error',
                            timestamp=timezone.now(),
                            note_type='RemovedFromGroup')

            to_remove = sled_user_qset.values_list('username',flat=True)
            if len(to_remove) > 1:
                myverb = 'Users %s were removed from the group.' % ','.join(to_remove)
            else:
                myverb = 'User %s was removed from the group.' % to_remove[0]
            action.send(owner,
                        target=self,
                        verb=myverb,
                        level='info',
                        action_type='RemovedFromGroup')


    def delete(self, *args, **kwargs):
        # notify group members.
        members = self.getAllMembers()
        for member in members:
            notify.send(sender=self.owner,
                        recipient=member,
                        verb='Group %s has been deleted.' % self.name,
                        level='warning',
                        timestamp=timezone.now(),
                        note_type='Deleted')

        super().delete(*args, **kwargs)  # Call the "real" delete() method.
