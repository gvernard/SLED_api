from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.apps import apps
from django.urls import reverse
from django.db.models import F

from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import assign_perm

from gm2m import GM2MField
from notifications.signals import notify
import inspect

from itertools import groupby
from operator import itemgetter

from . import SingleObject


class Collection(SingleObject):
    """
    Describes collections of SingleObjects, e.g. lenses, through a many-to-many relationship.

    Attributes:
        name (`str`): A name for the collection.
        description (`text`): What this collection is supposed to contain and what's its use.
        item_type (`str`): A choice of primary object type.
        myitems (): A generic many-to-many field
    """
    name = models.CharField(max_length=30,
                            help_text="A name for your collection")
    description = models.CharField(max_length=200,
                                   null=True,
                                   blank=True,
                                   help_text="A description for your collection"
                                   )
    myitems = GM2MField()
    ItemTypeChoices = (
        ('Lenses','Lenses'),
        ('Scores','Scores'),
        ('Models','Models')
    )
    item_type = models.CharField(max_length=100,
                                 choices=ItemTypeChoices,
                                 help_text="The type of items that should be in the collection.")

    class Meta(SingleObject.Meta):
        db_table = "collection"
        verbose_name = "collection"
        verbose_name_plural = "collections"
        ordering = ["modified_at"]
        # Constrain the number of objects in a collection?

    def get_absolute_url(self):
        return reverse('sled_collections:collections-detail',kwargs={'pk':self.id})

    def itemsOfWrongType(self,objects):
        """
        Ensures that the given items are all of the collection type.

        Raises:
            AssertionError: If the there are items in 'objects' that are not of the collection type.
        """
        wrong_type = []
        for obj in objects:
            if obj._meta.model.__name__ != self.item_type:
                wrong_type.append(obj)
        try:
            assert (len(wrong_type)==0),"The following items are not of the same type as the collection type: "
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise

    def itemsInCollection(self,objects):
        """
        Ensures that NONE of the given objects is in the collection.

        Raises:
            AssertionError: If there is even a single item in 'objects' that is already in the collection.
        """
        ids = []
        for obj in objects:
            ids.append(obj.id)
        existing = self.myitems.filter(gm2m_pk__in=ids)
        try:
            assert (existing.count()==0),"Some items are already in the collection."
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise

    def itemsNotInCollection(self,objects):
        """
        Ensures that ALL given objects are in the collection.

        Raises:
            AssertionError: If there is even a single item in 'objects' that is NOT already in the collection.
        """
        ids = []
        for obj in objects:
            ids.append(obj.id)
        existing = self.myitems.filter(gm2m_pk__in=ids)
        try:
            assert (existing.count()==len(objects)),"Some items to be removed are not already in the collection."
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
            
    def addItems(self,user,objects):
        """
        Adds the given items to the collection.
        Needs to check that everybody with access to the collection has access to these items as well.

        Args:
            user (User): the user calling this function, who has to be the owner of the collection it acts upon.
            objects (List[SingleObject]): A list of items to add to the collection. They have to match the collection type.

        Returns:
            string ("success"): if successful and no Assertion errors are raised. It also sends notifications if the collection is private or posts to the activity stream if public.

        Raises:
            AssertionError: if the user attempts to add private items to a public collection.
        """
        self.assertOwner(user) # Asserts that the user is the owner of the collection
        objects = self.convertToList(objects) # If input argument is a single value, convert to list
        self.itemsOfWrongType(objects) # Check if there are any items of the wrong type
        self.itemsInCollection(objects) # Check if items are already in the collection
            
        # Check if some items are private
        private_objects = []
        for obj in objects:
            if obj.access_level == 'PRI':
                private_objects.append(obj)

        # Get the ids of all the objects - required for notifying after a successful addition
        all_ids = []
        for obj in objects:
            all_ids.append(obj.id)

        if self.access_level == 'PRI':
            # Get everybody with access to this collection - required for notifying after a successful addition
            users_collection = list(self.getUsersWithAccess(user)) # Get the users with access to the collection
            users_collection.append(user) # Add the owner of the collection to the users with access
            groups_collection = list(self.getGroupsWithAccess(user)) # Get the groups with access to the collection
            print('Users/Groups with access to the COLLECTION: ',users_collection,groups_collection)
            
            if private_objects:
                # Check that collection owner really has view access to the private lenses
                has_perm = True
                perm = "view_" + private_objects[0]._meta.db_table
                checker = ObjectPermissionChecker(user)
                checker.prefetch_perms(private_objects)
                for obj in private_objects:
                    if not checker.has_perm(perm,obj):
                        has_perm = False
                try:
                    assert (has_perm),"User does not have access to private objects"
                except AssertionError as error:
                    caller = inspect.getouterframes(inspect.currentframe(),2)
                    print(error,"The operation of '"+caller[1][3]+"' should not proceed")
                    raise
                else:
                    self.myitems.add(*objects)
                    notify.send(sender=user,recipient=users_collection,verb='Objects have been added to private collection',level='warning',timestamp=timezone.now(),note_type='ItemsAdded',object_type=self.item_type,object_ids=all_ids)
                    for group in groups_collection:
                        notify.send(sender=user,recipient=group,verb='Objects have been added to private collection',level='warning',timestamp=timezone.now(),note_type='ItemsAdded',object_type=self.item_type,object_ids=all_ids)
                    return "success"
                
            else:
                # All items are public, proceed by adding them to the collection
                self.myitems.add(*objects)
                notify.send(sender=user,recipient=users_collection,verb='Objects have been added to private collection',level='warning',timestamp=timezone.now(),note_type='ItemsAdded',object_type=self.item_type,object_ids=all_ids)
                for group in groups_collection:
                    notify.send(sender=user,recipient=group,verb='Objects have been added to private collection',level='warning',timestamp=timezone.now(),note_type='ItemsAdded',object_type=self.item_type,object_ids=all_ids)
                return "success"
        else:
            try:
                assert (len(private_objects)==0),"A public collection cannot contain private items"
            except AssertionError as error:
                caller = inspect.getouterframes(inspect.currentframe(),2)
                print(error,"The operation of '"+caller[1][3]+"' should not proceed")
                raise
            else:
                self.myitems.add(*objects)                
                # Post to the activity stream
                return "success"
                                
    def removeItems(self,user,objects):
        """
        Remove the given items from the collection. Checks if items are of the right type.

        Args:
            user (User): the user calling this function, who has to be the owner of the collection it acts upon.
            objects (List[SingleObject]): A list of items to remove from the collection. They have to match the collection type.

        Returns:
            string ("success"): if successful and no Assertion errors are raised. It also sends notifications if the collection is private or posts to the activity stream if public.
        """
        self.assertOwner(user)
        objects = self.convertToList(objects)
        self.itemsOfWrongType(objects)
        self.itemsNotInCollection(objects) # Check if all items are already in the collection


        self.myitems.remove(*objects)
        if self.access_level == 'PRI':
            users_collection = list(self.getUsersWithAccess(user)) # Get the users with access to the collection
            users_collection.append(user) # Add the owner of the collection to the users with access
            groups_collection = list(self.getGroupsWithAccess(user)) # Get the groups with access to the collection
            all_ids = []
            for obj in objects:
                all_ids.append(obj.id)
            notify.send(sender=user,recipient=users_collection,verb='Objects have been removed from your private collection',level='warning',timestamp=timezone.now(),note_type='ItemsRemoved',object_type=self.item_type,object_ids=all_ids)
            for group in groups_collection:
                notify.send(sender=user,recipient=group,verb='Objects have been removed from your private collection',level='warning',timestamp=timezone.now(),note_type='ItemsRemoved',object_type=self.item_type,object_ids=all_ids)
        else:
            # Post to the activity stream
            pass
        return "success"

    def get_ugs_without_access(self):
        """
        Returns the users and groups that have acces to the collection but not to all the private objects in the collection.

        Returns:
            a dict: The dictionary has two entries, "users_per_obj" and "groups_per_obj". Each entry is the output of 'SingleObject._arrange_by_object'
        """
        private_objs = self.myitems.all().filter(access_level='PRI')

        # Check if users and groups have "view" permission
        obj_model = apps.get_model(app_label='lenses',model_name=self.item_type)
        objects_users = obj_model.accessible_objects.without_access(users_collection,private_objs)
        objects_groups = obj_model.accessible_objects.without_access(groups_collection,private_objs)
        mydict = {"users_per_obj":objects_users,"groups_per_obj":objects_groups}
        return mydict
                

    def ask_access_for_private(self,user):
        """
        Creates confirmation tasks for the owners of private objects in the collection for which the user does not have access.

        Args:
            user: a user instance.

        Returns:
            dict: a dictionary of usernames (str) for each owner and a list of all the ids they own

        Raises: 
            AssertionError: If the collection is not private.
        """
        
        try:
            assert (self.access_level=='PRI'),"Collection is not private"
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
        else:
            m2m_qset = self.myitems.all()
            ids = list(m2m_qset.values_list('gm2m_pk',flat=True))
            obj_model = apps.get_model(app_label='lenses',model_name=self.item_type)
            dum = list(obj_model.accessible_objects.in_ids(user,ids).values_list('id',flat=True))
            ids_acc = list(map(str,dum))
            set_difference = set(ids) - set(ids_acc)
            ids_priv = list(set_difference)

            mylist = obj_model.objects.filter(id__in=ids_priv,access_level='PRI').annotate(username=F('owner__username')).values('username','id')
            mylist = sorted(mylist,key = itemgetter('username'))
            
            owners_ids = {}
            for key,val in groupby(mylist,key=itemgetter('username')):
                tmp = []
                for k in val:
                    tmp.append(k['id'])
                owners_ids[key] = tmp
            
            return owners_ids



        
        
    

    
    
# Assign view permission to the owner of a new collection
@receiver(post_save,sender=Collection)
def handle_new_collection(sender,**kwargs):
    created = kwargs.get('created')
    if created: # a new collection was added
        collection = kwargs.get('instance')
        perm = 'view_'+collection._meta.db_table
        assign_perm(perm,collection.owner,collection)

