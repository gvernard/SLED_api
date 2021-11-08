from django.db import models
from django.contrib.auth.models import Group

#class SledGroups(models.Model):
class SledGroup(Group):
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
    description = models.CharField(max_length=200,null=True, blank=True)
    
    def __str__(self):
        return self.name

    class Meta():
        db_table = "sledgroups"
        verbose_name = "sledgroup"
        verbose_name_plural = "sledgroups"
        ordering = ["name"]
        # constrain on the Min and Max number of users that are members

    def getAllMembers(self):
        """
        Note:
            We may want to restrict this function to the owner, or to members only
        """
        users = self.user_set.all()
        return users
        
    def addMember(self,owner,seld_user):
        if owner.isOwner(self) and not sled_user.groups.filter(group__name=self.name):
            self.user_set.add(sled_user)
        
    def removeMember(self,owner,sled_user):
        if owner.isOwner(self) and sled_user.groups.filter(group__name=self.name):
            self.user_set.remove(sled_user)

    def __str__(self):
        return self.name

