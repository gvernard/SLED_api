from django.db.models.signals import pre_delete
from django.db.models import Count, Q
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.utils import timezone
from django.apps import apps

from notifications.signals import notify
from notifications.models import Notification
from guardian.shortcuts import get_objects_for_group,remove_perm,get_perms_for_model
from gm2m.signals import deleting
from actstream.models import Action

from lenses.models import Lenses, SingleObject, SledGroup, ConfirmationTask, Collection, AdminCollection



@receiver(pre_delete,sender=SledGroup)
def delete_group(sender,instance,**kwargs):
    members = instance.getAllMembers()

    # Notify group members
    for user in members:
        notify.send(sender=instance.owner,
                    recipient=user,
                    verb='DeletedGroupNote',
                    level='error',
                    timestamp=timezone.now(),
                    group_name=instance.name)

    # Remove permissions
    for model_class in SingleObject.__subclasses__():
        perm = 'view_'+model_class._meta.model_name
        pri_objs = model_class.objects.filter(access_level="PRI")
        objs = get_objects_for_group(instance,perm,klass=pri_objs) # This is a queryset
        if objs:
            remove_perm(perm,instance,objs)

    # Remove group's activity stream (where action target is the group)
    instance.target_actions.all().delete()
        
    # Remove notifications where the action_object is the group
    content_type_id = ContentType.objects.get_for_model(instance).id
    Notification.objects.filter(action_object_content_type_id=content_type_id).filter(action_object_object_id=instance.id).delete()
        
    # Remove AskToJoinGroup tasks pertinent to this group
    tasks = ConfirmationTask.objects.filter(task_type="AskToJoinGroup").values("id","cargo__object_ids")
    task_ids = []
    for task in tasks:
        if instance.id in task["cargo__object_ids"]:
            task_ids.append(task["id"])
    if task_ids:
        ConfirmationTask.objects.filter(id__in=task_ids).delete()



# If collection is private, notifying users and groups with access and removing permissions happens in the SingleObject.delete method.
@receiver(pre_delete,sender=Collection)
def delete_collection(sender,instance,**kwargs):
    # Remove collection's activity stream (where action target is the collection)
    instance.target_actions.all().delete()

    # Remove notifications where the action_object is the collection
    content_type_id = ContentType.objects.get_for_model(instance).id
    Notification.objects.filter(action_object_content_type_id=content_type_id).filter(action_object_object_id=instance.id).delete()

    # Remove actions from home activity stream



    


    
# Select all the AdminCollections that have only one or no item in them
# and remove the notifications and actions that are associated with them (also the AdminCollection itself)
@receiver(pre_delete,sender=Lenses)
@receiver(pre_delete,sender=Collection)
def remove_ad_col(sender,instance,**kwargs):
    content_type_id = ContentType.objects.get_for_model(AdminCollection).id
    adcols = instance.admincollection_set.annotate(Nitems=Count('admincollection_myitems')).filter( Q(Nitems=1) | Q(Nitems=0) )
    for adcol in adcols:
        Notification.objects.filter(action_object_content_type_id=content_type_id).filter(action_object_object_id=adcol.id).delete()
        Action.objects.action_object(adcol).delete()
        adcol.delete()
