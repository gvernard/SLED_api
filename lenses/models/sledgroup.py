from django.db import models
from django.contrib.auth.models import Group
from django.urls import reverse

from . import SingleObject

#class SledGroups(models.Model):
class SledGroup(Group,SingleObject):
    """
    The custom SLED model for a group of users, inheriting from the django `Group`.

    Attributes:
        description(`str`): A short description of the group's purpose.

    Todo:
        - Should this be a SingleObject? If so then the access_level should always be set to public and we will not be using access related functions.
        - Related to the above, it doesn't make sense to have collections of groups, so no need to use the addToCollection, etc, functions.

    """
#    group = models.OneToOneField(Group,
#                                 on_delete=models.CASCADE,
#                                 primary_key=True
#                                 )
    #owner = models.ForeignKey('Users',on_delete=models.CASCADE) 
    description = models.CharField(max_length=200,null=True, blank=True)

    
    class Meta():
        db_table = "sledgroups"
        verbose_name = "sledgroup"
        verbose_name_plural = "sledgroups"
        ordering = ["name"]
        # constrain on the Min and Max number of users that are members?

        
    def save(self,*args,**kwargs):
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
