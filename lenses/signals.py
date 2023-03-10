from django.db.models.signals import pre_delete
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.utils import timezone

from notifications.signals import notify
from notifications.models import Notification
from guardian.shortcuts import get_objects_for_group,remove_perm,get_perms_for_model

from lenses.models import Lenses, SingleObject, SledGroup, ConfirmationTask



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
    #group = Group.objects.get(id=self.id)
    for model_class in SingleObject.__subclasses__():
        perm = 'view_'+model_class._meta.db_table
        pri_objs = model_class.objects.filter(access_level="PRI")
        objs = get_objects_for_group(instance,perm,klass=pri_objs)
        if objs:
            remove_perm(perm,self,*objs)

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
