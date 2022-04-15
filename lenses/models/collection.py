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
import simplejson as json
from actstream import action
from dirtyfields import DirtyFieldsMixin

import inspect
from itertools import groupby
from operator import itemgetter

from . import SingleObject



class Collection(SingleObject,DirtyFieldsMixin):
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
    myitems = GM2MField('Lenses')
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

        
    def save(self,*args,**kwargs):
        dirty = self.get_dirty_fields(verbose=True)
        if len(dirty) > 0:
            action.send(self.owner,
                        target=self,
                        verb="Fields have been updated",
                        level='success',
                        action_type='UpdateSelf',
                        object_type='Collection',
                        fields=json.dumps(dirty))

        super().save(*args,**kwargs)

        
    def __str__(self):
        return self.name

    
    def get_absolute_url(self):
        return reverse('sled_collections:collections-detail',kwargs={'pk':self.id})

    
    def itemsOfWrongType(self,objects):
        """
        Ensures that the given items are all of the collection type.

        Raises:
            AssertionError: If the there are items in 'objects' that are not of the collection type.
        """
        try:
            wrong_type = []
            for obj in objects:
                if obj._meta.model.__name__ != self.item_type:
                    wrong_type.append(obj)
            assert (len(wrong_type)==0),"The following items are not of the same type as the collection type: "
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise


    def getSpecificModelInstances(self,user):
        """
        Returns specific model instances instead of gm2m

        Args:
            user (User): the user making the query
            
        Returns:
            objects (queryset): a queryset of item_type objects.
        """
        obj_model = apps.get_model(app_label='lenses',model_name=self.item_type)
        ids = list(self.myitems.all().values_list('gm2m_pk',flat=True))
        objects = obj_model.accessible_objects.in_ids(user,ids)
        return objects
        

    def getNoAccess(self,user):
        obj_model = apps.get_model(app_label='lenses',model_name=self.item_type)
        ids = list(self.myitems.all().values_list('gm2m_pk',flat=True))
        acc = obj_model.accessible_objects.in_ids(user,ids)
        all = obj_model.accessible_objects.in_ids(self.owner,ids)
        no_acc = all.order_by().difference(acc.order_by())
        return no_acc

    
    def itemsInCollection(self,user,objects):
        """
        Ensures that NONE of the given objects is in the collection.

        Args:
            user: the user making the request.
            objects: a queryset of objects.

        Returns:
            existing_objects: A queryset with the input objects that are already in the collection, if any
        """
        in_collection_ids = self.myitems.all().values_list('gm2m_pk',flat=True)
        obj_model = apps.get_model(app_label='lenses',model_name=self.item_type)
        in_collection = obj_model.accessible_objects.in_ids(user,in_collection_ids)
        copies = in_collection & objects
        return copies

    
    def itemsNotInCollection(self,user,objects):
        """
        Ensures that ALL given objects are in the collection.

        Args:
            user: the user making the request.
            objects: a queryset of objects.

        Returns:
            not_in: A queryset with the input objects that are NOT already in the collection, if any
        """
        in_collection_ids = self.myitems.all().values_list('gm2m_pk',flat=True)
        obj_model = apps.get_model(app_label='lenses',model_name=self.item_type)
        in_collection = obj_model.accessible_objects.in_ids(user,in_collection_ids).order_by()
        not_in = objects.order_by().difference(in_collection)
        return not_in

    
    def addItems(self,user,objects):
        """
        Adds the given items to the collection.
        Needs to check that everybody with access to the collection has access to these items as well.

        Args:
            user (User): the user calling this function, who has to be the owner of the collection it acts upon.
            objects (queryset): A queryset of items to add to the collection. They have to match the collection type.

        Returns:
            string ("success"): if successful and no Assertion errors are raised. It also sends notifications if the collection is private or posts to the activity stream if public.
        Raises:
            AssertionError: if the user attempts to add private items to a public collection.
        """
        self.assertOwner(user) # Asserts that the user is the owner of the collection
        self.itemsOfWrongType(objects) # Check if there are any items of the wrong type

        try:
            copies = self.itemsInCollection(user,objects) # Check if items are already in the collection
            assert (len(copies)==0),"Items already in the collection"
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
            
        # Check if some items are private
        private_objects = []
        for obj in objects:
            if obj.access_level == 'PRI':
                private_objects.append(obj)

        if self.access_level == 'PRI':
            if private_objects:
                try:
                    # Check that collection owner really has view access to the private lenses
                    has_perm = True
                    perm = "view_" + private_objects[0]._meta.db_table
                    checker = ObjectPermissionChecker(user)
                    checker.prefetch_perms(private_objects)
                    for obj in private_objects:
                        if not checker.has_perm(perm,obj):
                            has_perm = False
                    assert (has_perm),"User does not have access to private objects"
                except AssertionError as error:
                    caller = inspect.getouterframes(inspect.currentframe(),2)
                    print(error,"The operation of '"+caller[1][3]+"' should not proceed")
                    raise
                else:
                    N_new = self.finalizeAddItems(user,objects)
                    return N_new                
            else:
                # All items are public, proceed by adding them to the collection
                N_new = self.finalizeAddItems(user,objects)
                return N_new
        else:
            try:
                assert (len(private_objects)==0),"A public collection cannot contain private items"
            except AssertionError as error:
                caller = inspect.getouterframes(inspect.currentframe(),2)
                print(error,"The operation of '"+caller[1][3]+"' should not proceed")
                raise
            else:
                N_new = self.finalizeAddItems(user,objects)
                return N_new

            
    def finalizeAddItems(self,user,objects):
        self.myitems.add(*objects)        

        action.send(self.owner,
                    target=self,
                    verb="Items added to the colletion.",
                    level='success',
                    action_type='AddedToCollection',
                    object_type=objects[0]._meta.model.__name__,
                    object_ids=[obj.id for obj in objects])

        # Return the number of inserted items
        response = {"status":"ok","N_added":len(objects)}
        return response

    
    def removeItems(self,user,objects):
        """
        Remove the given items from the collection. Checks if items are of the right type.

        Args:
            user (User): the user calling this function, who has to be the owner of the collection it acts upon.
            objects (queryset): A list of items to remove from the collection. They have to match the collection type.

        Returns:
            string ("success"): if successful and no Assertion errors are raised. It also sends notifications if the collection is private or posts to the activity stream if public.
        """
        self.assertOwner(user)
        self.itemsOfWrongType(objects)

        try:
            not_in = self.itemsNotInCollection(user,objects) # Check if items are already in the collection
            assert (len(not_in)==0),"Items NOT already in the collection"
        except AssertionError as error:
            caller = inspect.getouterframes(inspect.currentframe(),2)
            print(error,"The operation of '"+caller[1][3]+"' should not proceed")
            raise
        
        self.myitems.remove(*objects)
        N_removed = objects.count()

        action.send(self.owner,
                    target=self,
                    verb="Items removed from the colletion.",
                    level='success',
                    action_type='RemovedFromCollection',
                    object_type=objects[0]._meta.model.__name__,
                    object_ids=[obj.id for obj in objects])

        response = {"status":"ok","N_removed":N_removed}
        return response

    
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

