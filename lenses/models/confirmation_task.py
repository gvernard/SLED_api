from django.db import models,connection
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core import serializers
from django.core.files.storage import default_storage
from django.urls import reverse
from django import forms
from django.db.models import Q,F,Count,CharField
from django.apps import apps
from django.conf import settings
from django.template.loader import get_template
from django.template.response import TemplateResponse

from guardian.shortcuts import assign_perm

from notifications.signals import notify
from actstream import action
from actstream.actions import unfollow
from actstream.models import followers,following

import abc
import json
import os
import string
import random
import shutil

from . import Lenses, SingleObject, Collection, SledGroup, AdminCollection



class ConfirmationTaskManager(models.Manager):
    def pending_for_user(self,user):
        return super().get_queryset().filter(status='P').filter(Q(owner=user)|Q(recipients__username=user.username))

    def completed_for_user(self,user):
        return super().get_queryset().filter(status='C').filter(Q(owner=user)|Q(recipients__username=user.username))

    def all_as_recipient(self,user):
        return super().get_queryset().filter(Q(recipients__username=user.username))

    def all_as_owner_only(self,user):
        return super().get_queryset().filter(owner=user).exclude(Q(recipients__username=user.username))
    
    def all_as_recipient_only(self,user):
        return super().get_queryset().filter(Q(recipients__username=user.username)).exclude(owner=user)

    def both_owner_recipient(self,user):
        return super().get_queryset().filter( Q(recipients__username=user.username) & Q(owner=user) )

    def check_pending_tasks(self,obj_type,obj_ids,task_types=None):
        """
        Provides access to all the objects that the user owns, arranged by type.

        Args:
            obj_type: the model name 
            obj_ids: A list of object ids
            task_types: A list of task types to search for (see below)

        Returns:
            list: A list of dictionaries containing each task and the list of objects in it.
            str: A corresponding html ul element with the links to each task and objects it contains.
        """
        model_ref = apps.get_model(app_label='lenses',model_name=obj_type)
        qset = model_ref.objects.filter(id__in=obj_ids)
        obj_list = list(qset)
        set_ids = set(obj_ids)
        dictionary = dict(zip(obj_ids,obj_list))

        if task_types:
            tmp = ConfirmationTask.objects.none()
            for id in obj_ids:
                tasks = super().get_queryset().filter(status='P').filter(cargo__object_type=obj_type).filter(cargo__object_ids__contains=id).filter(task_type__in=task_types)
                if tasks:
                    tmp = tmp|tasks
            tasks = tmp
        else:
            tmp = ConfirmationTask.objects.none()
            for id in obj_ids:
                tasks = super().get_queryset().filter(status='P').filter(cargo__object_type=obj_type).filter(cargo__object_ids__contains=id)
                if tasks:
                    tmp = tmp|tasks
            tasks = tmp
            
        tasks_objects = []
        for task in tasks:
            json = task.cargo
            set_task_ids = set(json["object_ids"])
            intersection = list(set_task_ids.intersection(set_ids))
            if len(intersection) > 0:
                objs_in_task = [ dictionary[key] for key in intersection ]
                tasks_objects.append( {"task":task,"objs":objs_in_task} )

        errors = []
        if len(tasks_objects) > 0:
            for item in tasks_objects:
                error_txt = 'Existing <a href="'+item["task"].get_absolute_url()+'">'+item["task"].task_type+' task</a> contains '
                if len(item["objs"]) > 1:
                    error_txt += model_ref._meta.verbose_name_plural.title()
                else:
                    error_txt += model_ref._meta.verbose_name.title()
                error_txt += ': '
                error_txt += '<ul>'
                for obj in item["objs"]:
                    error_txt += '<li><a href="'+obj.get_absolute_url()+'">'+obj.__str__()+'</a></li>'
                error_txt += '</ul>'
                errors.append(error_txt)
                
        return tasks_objects,errors
                
        

                
                
class ConfirmationTask(SingleObject):
    """
    The Confirmation task object.

    Attributes:
        task_name (str): the name of the task to perform.
        status (`enum`): completed if all the users have responded, otherwise pending.
        cargo (json): a JSON object that carries information necessary to complete the task once all responses have been received.
        recipients (`QuerySet`): A set of Users.

    Todo:
        - Associate the task name to a class (classes of confirmation task types will need to be implemented first). 
    """

    # The task types MUST match 1-to-1 the proxy models below
    TaskTypeChoices = (
        ('CedeOwnership','Cede ownership'),
        ('MakePrivate','Make private'),
        ('DeleteObject','Delete public object'),
        ('ResolveDuplicates','Resolve duplicate objects'),
        ('MergeLenses','Merge lenses'),
        ('AskPrivateAccess','Ask access to private objects'),
        ('AskToJoinGroup','Request to add to group'),
        ('AddData','Associate data to lens.'),
        ('AcceptNewUser','Accept new user'),
        ('InspectImages','Inspect images before making them PUB'),
    )
    task_type = models.CharField(max_length=100,
                                 choices=TaskTypeChoices,
                                 help_text="The name of the task to perform.") 
    StatusTypeChoices = (
        ("P",'Pending'),
        ("C",'Completed')
    )
    status = models.CharField(max_length=1,
                              choices=StatusTypeChoices,
                              default="P",
                              help_text="Status of the task: 'Pending' (P) or 'Completed' (C).")
    cargo = models.JSONField(help_text="A json object holding any variables that will be executed upon completion of the task.")
    recipients = models.ManyToManyField(
        'Users',
        related_name='confirmation_tasks',
        through='ConfirmationResponse',
        through_fields=('confirmation_task','recipient'),
        help_text="A many-to-many relationship between ConfirmationTask and Users that will need to respond."
    )
    recipient_names = []

    custom_manager = ConfirmationTaskManager()
    objects = models.Manager()
    
    class Meta():
        db_table = "confirmation_tasks"
        verbose_name = "task"
        verbose_name_plural = "tasks"
        ordering = ["-status","-modified_at"]
        # constrain the number of recipients?
        
    def __init__(self, *args, **kwargs):
        super(ConfirmationTask,self).__init__(*args, **kwargs)
        subclass_found = False
        for _class in ConfirmationTask.__subclasses__():
            if self.task_type == _class.__name__:
                self.__class__ = _class
                subclass_found = True
                break
        if not subclass_found:
            raise ValueError(task_type)

    def __str__(self):
        return '%s_%s' % (self.task_type,str(self.id))

    def get_absolute_url(self):
        if self.owner.is_superuser: # This refers to the django user 'admin'
            return reverse('sled_tasks:tasks-detail-admin-owner',kwargs={'pk':self.id})
        else:
            return reverse('sled_tasks:tasks-detail-owner',kwargs={'pk':self.id})

    def create_task(sender,users,task_type,cargo):
        """
        Creates a task and assigns the recipients (list of users) to it via a many-to-many relation.

        It also invites the recipients by sending them a link via email.

        Args:
            sender (`User`): An instance of a `User` object.
            users (`QuerySet`): A queryset of User objects.
            task_type (str): The name of the task to perform once all users have responded.
            cargo (JSON): a JSON object with information required to complete the task.

        Returns:
            bool: True if the given user is the owner, False otherwise.
        """
        task = ConfirmationTask(owner=sender,task_type=task_type,cargo=cargo)
        task.save()
        task.recipients.set(users)
        task.save()
        task.recipient_names = list(users.values_list('username',flat=True))
        task.inviteRecipients(task.recipients.all())
        return task

    def load_task(task_id):
        """
        Loads a task based on the given id.

        If the task exists it returns it and sets the recipient_names variables, otherwise it returns None.

        Args:
            task_id (int): An integer representing the task id.

        Returns:
            ConfirmationTask object: if successful, otherwise None.
        """
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
            task.recipient_names = list(task.recipients.values_list('username',flat=True))
        except ConfirmationTask.DoesNotExist:
            task = None
        return task

    def inviteRecipients(self,users):
        """
        Emails list of recipients to inform/remind them that a confirmation task requires their response

        Args:
            recipients (`QuerySet`): A queryset of User objects.
        """
        site = Site.objects.get_current()
        subject = 'SLED: Response to %s task required' % self.task_type
        from_email = 'no-reply@%s' % site.domain
        
        for user in users:
            html_message = get_template('emails/task_notification.html')
            mycontext = {
                'first_name': user.first_name,
                'task_type': self.task_type,
                'protocol': 'http',
                'domain': site.domain,
                'task_url': reverse('sled_tasks:tasks-list')
            }
            html_message = html_message.render(mycontext)
            plain_message = strip_tags(html_message)
            recipient_email = user.email
            send_mail(subject,plain_message,from_email,[recipient_email],html_message=html_message)
            
    def get_all_recipients(self):
        """
        Gets all the recipients of the confirmation task. 
         
        Returns:
            A QuerySet with User objects.
        """
        return self.recipients.all()

    def get_all_responses(self):
        """
        Gets all the responses for the confirmation task. 
         
        Returns:
            A QuerySet with ConfirmationResponse objects.
        """
        return self.recipients.through.objects.filter(confirmation_task__exact=self.id)

    def not_heard_from(self):
         """
         Checks which recipients have not responded yet. 
         
         Returns:
             A QuerySet with ConfirmationResponse objects.
         """
         return self.recipients.through.objects.filter(confirmation_task__exact=self.id,response__exact='')

    def heard_from(self):
         """
         Checks which recipients have already responded. 
         
         Returns:
             A QuerySet with ConfirmationResponse objects.
         """
         return self.recipients.through.objects.filter(confirmation_task__exact=self.id).exclude(response__exact='')

    def registerResponse(self,user,response,comment):
        """
        Registers the given users response to the confirmation task
        """
        if user not in self.recipients.all():
            raise ValueError(self.recipient_names,user.username) # Need custom exception here
        if response not in self.allowed_responses(): 
            raise ValueError(response) # Need custom exception here
        self.recipients.through.objects.filter(confirmation_task=self,recipient=user).update(response=response,response_comment=comment,created_at=timezone.now())
        #self.finalizeTask()
        #self.recipients.through.objects.filter(confirmation_task=self,recipient=user).update(response='',response_comment=comment)
        

    def registerAndCheck(self,user,response,comment):
        """
        Registers the given recipients response and checks if all recipients have replied. If yes, calls finalizeTask and updates the status to completed.
        """
        self.registerResponse(user,response,comment)
        nhf = self.not_heard_from()
        if nhf.count() == 0:
            self.finalizeTask()
            self.status = "C"
            self.save()


    # To be overwritten by the proxy models
    #@property
    #@abc.abstractmethod
    def allowed_responses(self):
        pass

    # To be overwritten by the proxy models
    #@abc.abstractmethod
    def finalizeTask(self):
        pass


    
class ConfirmationResponse(models.Model):
    confirmation_task = models.ForeignKey(ConfirmationTask, on_delete=models.CASCADE)
    recipient = models.ForeignKey('Users',on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    response = models.CharField(max_length=1000, help_text="The response of a given user to a given confirmation task.") 
    response_comment = models.CharField(max_length=100, help_text="A comment (optional) from the recipient on the given response.") 




class DeleteObject(ConfirmationTask):
    class Meta:
        proxy = True
        
    def allowed_responses(self):
        return ['yes','no']

    def finalizeTask(self):
        responses = self.heard_from().annotate(name=F('recipient__username')).values_list('response',flat=True)
        
        from . import Users
        admin = Users.getAdmin().first()
        if len(set(responses)) == 1 and responses[0] == 'yes':
            #cargo = json.loads(self.cargo)
            #getattr(.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids']).delete()
            objs = apps.get_model(app_label="lenses",model_name=self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            notify.send(sender=admin,
                        recipient=self.owner,
                        verb='DeleteObjectsAcceptedNote',
                        level='success',
                        timestamp=timezone.now(),
                        action_object=self)

            if self.cargo['object_type'] != 'Collection':
                uqset = self.owner.get_collection_owners(objs)
                users = list(set( uqset ))
                for u in users:
                    self.owner.remove_from_third_collections(objs,u)

            if self.cargo['object_type'] != 'Lenses':
                objs.delete()
            else:

                ### Unfollow lens ####################################################################
                for lens in objs:
                    lens_followers = followers(lens)
                    for user in lens_followers:
                        unfollow(user,lens,send_action=False)
                    
                ### Remove these lenses from any linked papers
                qset = apps.get_model(app_label="lenses",model_name='Paper').objects.filter(lenses_in_paper__id__in=self.cargo['object_ids'])
                for paper in qset:
                    paper.lenses_in_paper.remove(*objs)
                
                ### Delete linked data: Redshifts, Imaging, Spectrum, and Catalogue
                for user,lenses_ids in self.cargo['users_lenses'].items():
                    print("For user: ",user)
                    qset = apps.get_model(app_label="lenses",model_name='Redshift').objects.filter(Q(access_level="PUB") & Q(lens__id__in=lenses_ids) & Q(owner__username=user))
                    print(qset)
                    qset.delete()
                    qset = apps.get_model(app_label="lenses",model_name='Imaging').objects.filter(Q(access_level="PUB") & Q(lens__id__in=lenses_ids) & Q(owner__username=user))
                    print(qset)
                    qset.delete()
                    qset = apps.get_model(app_label="lenses",model_name='Spectrum').objects.filter(Q(access_level="PUB") & Q(lens__id__in=lenses_ids) & Q(owner__username=user))
                    print(qset)
                    qset.delete()
                    qset = apps.get_model(app_label="lenses",model_name='Catalogue').objects.filter(Q(access_level="PUB") & Q(lens__id__in=lenses_ids))
                    qset.delete()
                    print(qset)

                objs.delete()
                
                    
        else:
            notify.send(sender=admin,
                        recipient=self.owner,
                        verb='DeleteObjectsRejectedNote',
                        level='error',
                        timestamp=timezone.now(),
                        action_object=self)

            
class CedeOwnership(ConfirmationTask):
    class Meta:
        proxy = True

    def allowed_responses(self):
        return ['yes','no']

    def finalizeTask(self,**kwargs):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        heir = self.get_all_recipients()[0]
        if response == 'yes':
            #cargo = json.loads(self.cargo)
            #objs = getattr(lenses.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            object_type = self.cargo['object_type']
            model_ref = apps.get_model(app_label="lenses",model_name=object_type)
            objs = model_ref.objects.filter(pk__in=self.cargo['object_ids'])
            pri = []
            pub = []
            for obj in objs:
                obj.owner=heir
                obj.save()
                if obj.access_level == 'PRI':
                    pri.append(obj)
                else:
                    pub.append(obj)

            # Heir to unfollow any of the inherited objects
            if object_type == 'Lenses':
                set_followed = set(following(heir,Lenses))
                set_lenses = set(objs)
                intersection = list(set_followed.intersection(set_lenses))
                if len(intersection) > 0:
                    for lens in intersection:
                        unfollow(heir,lens)
                    ad_col = AdminCollection.objects.create(item_type=object_type,myitems=intersection)
                    notify.send(sender=heir,
                                recipient=heir,
                                verb='HeirUnfollowNote',
                                level='warning',
                                timestamp=timezone.now(),
                                action_object=ad_col)
                    
            # Handle public objects
            if pub and object_type != 'SledGroup':
                from . import Users
                ad_col = AdminCollection.objects.create(item_type=object_type,myitems=pub)
                action.send(self.owner,target=Users.getAdmin().first(),verb='CedeOwnershipHome',level='info',action_object=ad_col,previous_id=self.owner.id,next_id=heir.id)
                    
            # Handle private objects
            if pri:
                perm = 'view_' + model_ref._meta.model_name
                # Below I have to loop over each object individually because of the way assign_perm is coded.
                # If the given obj is a list, the it calls bulk_assign_perms that checks for any permission (including through a group) using ObjectPermissionChecker.
                # As a result, if a user already has access through a group explicit permission (user-object pair) is not created.
                for obj in pri:
                    assign_perm(perm,heir,obj) # assign view permission to the new owner for the private lenses

                if object_type != 'SledGroup':
                    # Notify users with access (except the previous owner, who has access already)
                    users_with_access,accessible_objects = heir.accessible_per_other(pri,'users')
                    for i,user in enumerate(users_with_access):
                        if user.id != self.owner.id:
                            objects = []
                            for j in accessible_objects[i]:
                                objects.append(pri[j])
                            ad_col = AdminCollection.objects.create(item_type=object_type,myitems=objects)
                            notify.send(sender=self.owner,
                                        recipient=user,
                                        verb='CedeOwnershipNote',
                                        level='info',
                                        timestamp=timezone.now(),
                                        action_object=ad_col,
                                        previous_id=self.owner.id,
                                        next_id=heir.id)
                        
                    # Notify groups with access
                    groups_with_access,accessible_objects = heir.accessible_per_other(pri,'groups')
                    id_list = [g.id for g in groups_with_access]
                    gwa = SledGroup.objects.filter(id__in=id_list) # Needed to cast Group to SledGroup
                    for i,group in enumerate(groups_with_access):
                        objects = []
                        for j in accessible_objects[i]:
                            objects.append(pri[j])
                        ad_col = AdminCollection.objects.create(item_type=object_type,myitems=objects)
                        action.send(self.owner,target=gwa[i],verb='CedeOwnershipGroup',level='info',action_object=ad_col,previous_id=self.owner.id,next_id=heir.id)
                
            # Confirm to the previous owner
            notify.send(sender=heir,
                        recipient=self.owner,
                        verb='CedeOwnershipAcceptedNote',
                        level='success',
                        timestamp=timezone.now(),
                        action_object=self)

        else:
            notify.send(sender=heir,
                        recipient=self.owner,
                        verb='CedeOwnershipRejectedNote',
                        level='error',
                        timestamp=timezone.now(),
                        action_object=self)

        
class MakePrivate(ConfirmationTask):
    class Meta:
        proxy = True
        
    def allowed_responses(self):
        return ['yes','no']

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        from . import Users
        admin = Users.getAdmin().first()
        model_ref = apps.get_model(app_label="lenses",model_name=self.cargo['object_type'])
        objs = model_ref.objects.filter(pk__in=self.cargo['object_ids'])
        if response == 'yes':
            #cargo = json.loads(self.cargo)
            #objs = getattr(lenses.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])

            perm = "view_"+objs[0]._meta.model_name
            assign_perm(perm,self.owner,objs) # objs here can be a list because public objects should not have any permissions associated with them anyway
            notify.send(sender=admin,
                        recipient=self.owner,
                        verb='MakePrivateAcceptedNote',
                        level='success',
                        timestamp=timezone.now(),
                        action_object=self)

            if self.cargo['object_type'] not in ['Collection','Imaging','Spectrum','Catalogue']:
                uqset = self.owner.get_collection_owners(objs)
                users = list(set( uqset.exclude(username=self.owner.username) ))
                for u in users:
                    self.owner.remove_from_third_collections(objs,u)

            # Unfollow lenses (nobody has access to these private lenses yet)
            if self.cargo['object_type'] == 'Lenses':
                users = {}
                for lens in objs:
                    uf = followers(lens)
                    for u in uf:
                        if u.username in users.keys():
                            users[u.username]["lenses"].append(lens)
                        else:
                            users[u.username] = {"user":u,"lenses":[lens]}
                        unfollow(u,lens)
                for u,mydict in users.items():
                    ad_col = AdminCollection.objects.create(item_type='Lenses',myitems=mydict["lenses"])
                    notify.send(sender=self.owner,
                                recipient=mydict["user"],
                                verb='MakePrivateUnfollowNote',
                                level='warning',
                                timestamp=timezone.now(),
                                action_object=ad_col)
                    
            # Finally update the objects' access_level to private
            for obj in objs:
                obj.access_level='PRI'
                obj.save()

        else:
            notify.send(sender=admin,
                        recipient=self.owner,
                        verb='MakePrivateRejectedNote',
                        level='error',
                        timestamp=timezone.now(),
                        action_object=self)
        

class ResolveDuplicates(ConfirmationTask):
    class Meta:
        proxy = True

    responses_allowed = []
    
    def allowed_responses(self):
        return self.responses_allowed

    def finalizeTask(self):
        # First find the lenses that where selected as duplicates (to be rejected)
        obj_responses = self.heard_from().annotate(name=F('recipient__username')).values('response').first()
        objects = list(serializers.deserialize("json",self.cargo['objects']))
        mode = self.cargo['mode']
        messages = []
        responses = json.loads(obj_responses['response'])
        index_insert = {}
        for response in responses:
            index_insert[response["index"]] = response["insert"]
        
        # Split objects according to response
        objs_to_add = []
        objs_to_make_public = []
        objs_to_merge = []
        objs_to_merge_in = []
        for i in range(0,len(objects)):
            index = str(i)
            if index in index_insert.keys():
                if index_insert[index] == 'yes':
                    if mode == "makePublic":
                        objs_to_make_public.append(objects[i])
                    else:
                        objs_to_add.append(objects[i])
                elif index_insert[index] == 'no':
                    # Remove uploaded image if the object is new
                    if not objects[i].object.pk:
                        default_storage.mydelete(objects[i].object.mugshot.name)
                else:
                    objs_to_merge.append(objects[i])
                    objs_to_merge_in.append(index_insert[index])
            else:
                if mode == "makePublic":
                    objs_to_make_public.append(objects[i])
                else:
                    objs_to_add.append(objects[i])
                
                    
        if len(objs_to_make_public) > 0:
            ids = [obj.object.pk for obj in objs_to_make_public]
            lenses = apps.get_model(app_label="lenses",model_name='Lenses').accessible_objects.in_ids(self.owner,ids)
            cargo = {'object_type': 'Lenses',
                     'object_ids': ids,
                     }
            from . import Users
            receiver = Users.selectRandomInspector()
            mytask = ConfirmationTask.create_task(self.owner,receiver,'InspectImages',cargo)
            messages.append("An <strong>InspectImages</strong> task has been submitted!")
            

        if len(objs_to_add) > 0:
            pri = []
            pub = []
            for obj in objs_to_add:
                obj.object.owner = self.owner
                if obj.object.access_level == 'PRI':
                    pri.append(obj.object)
                else:
                    obj.object.access_level = 'PRI' # Save all lenses as PRI, create a InspectImage task for PUB lenses
                    pub.append(obj.object)

            # Insert in the database
            for lens in (pri+pub):
                lens.save()
            assign_perm('view_lenses',self.owner,(pri+pub))

            if pub:
                # Create a InspectImages task
                cargo = {'object_type': 'Lenses',
                         'object_ids': [ lens.id for lens in pub ],
                         }
                from . import Users
                receiver = Users.selectRandomInspector()
                mytask = ConfirmationTask.create_task(self.owner,receiver,'InspectImages',cargo)

        if len(objs_to_merge) > 0:
            # Create merge task

            # Fetch all the existing lenses
            ids = [int(id) for id in objs_to_merge_in]
            existing = apps.get_model(app_label="lenses",model_name='Lenses').accessible_objects.in_ids(self.owner,ids)
            
            for i in range(0,len(objs_to_merge)):
                if mode == "add":
                    # Create a new PRI lens
                    if objs_to_merge[i].object.name == objs_to_merge[i].object.create_name():
                        letters = string.ascii_lowercase
                        rand = ''.join(random.choice(letters) for i in range(3))
                        objs_to_merge[i].object.name = 'tmp_'+rand+'_'+objs_to_merge[i].object.name
                    objs_to_merge[i].object.owner = self.owner
                    objs_to_merge[i].object.mugshot.name = objs_to_merge[i].object.mugshot.name
                    objs_to_merge[i].object.access_level = 'PRI'
                    objs_to_merge[i].object.save()
                    assign_perm('view_lenses',self.owner,objs_to_merge[i].object)

                cargo = {
                    'new_lens': objs_to_merge[i].object.pk,
                    'existing_lens': existing[i].pk,
                    'object_type': 'Lenses',
                    'object_ids': [existing[i].pk,objs_to_merge[i].object.pk]
                }
                from . import Users
                receiver = Users.objects.filter(id=existing[i].owner.id) # receiver must be a queryset
                mytask = ConfirmationTask.create_task(self.owner,receiver,'MergeLenses',cargo)

            
        if len(objs_to_merge) == 0:
            messages.append('Duplicates resolved successfully!')
        else:
            # Create a more custom message informing about merge tasks etc. Maybe a new template is needed?
            messages.append( 'Merge tasks have been created for %d lenses, whose owners have been notified!' % len(objs_to_merge) )
        return '<br>'.join(messages)
            


class MergeLenses(ConfirmationTask):
    class Meta:
        proxy = True
        
    responses_allowed = []
    
    def allowed_responses(self):
        return self.responses_allowed

    def finalizeTask(self):
        # Switch the selected data and all PRI data from the submitted lens to the existing one
        # Update any fields of the existing lens from the submitted one
        obj_responses = self.heard_from().annotate(name=F('recipient__username')).values('response').first()
        response = json.loads(obj_responses['response'])

        if response['response'] == 'yes':
            from . import Users
            admin = Users.getAdmin().first()

            target = Lenses.objects.get(id=self.cargo["existing_lens"])
            new = Lenses.objects.get(id=self.cargo["new_lens"])

            # First, transfer the data that were selected by the target lens owner to merge
            flag = False
            redshift_ids = []
            imaging_ids = []
            spectrum_ids = []
            generic_image_ids = []
            for item in response['items']:
                dum = item.split('-')
                obj_name = dum[0]
                if obj_name == 'Field':
                    field_name = dum[1]
                    if field_name == 'info':
                        new_value = getattr(new,field_name)
                        old_value = getattr(target,field_name)
                        setattr(target,field_name,old_value+'. '+new_value)
                    elif field_name == 'mugshot':
                        # Create a GenericImage from the old mugshot
                        model_ref = apps.get_model(app_label="lenses",model_name='GenericImage')
                        old_mug = model_ref(lens=target,owner=new.owner,access_level=target.access_level,name='Old mugshot',info='A previous mugshot image of the lens.',image=target.mugshot)
                        old_mug.save()

                        dum,file_ext = os.path.splitext(new.mugshot.name)
                        tmp_name = os.path.join('temporary',new.owner.username,str(self.id)+file_ext)
                        default_storage.copy(new.mugshot.name,tmp_name)
                        target.mugshot.name = tmp_name
                    else:
                        new_value = getattr(new,field_name)
                        setattr(target,field_name,new_value)
                    flag = True
                elif obj_name == 'Redshift':
                    redshift_ids.append(dum[1])
                elif obj_name == 'Imaging':
                    imaging_ids.append(dum[1])
                elif obj_name == 'Spectrum':
                    spectrum_ids.append(dum[1])
                elif obj_name == 'GenericImage':
                    generic_image_ids.append(dum[1])
                else:
                    # Raise error
                    pass
            if flag:
                target.save()
                ad_col = AdminCollection.objects.create(item_type="Lenses",myitems=[target])
                target_owner = self.get_all_recipients()[0]
                action.send(target_owner,target=admin,verb='UpdateHome',level='info',action_object=ad_col)
            

            if redshift_ids:
                redshifts = apps.get_model(app_label="lenses",model_name='Redshift').objects.filter(id__in=redshift_ids)
                for redshift in redshifts:
                    redshift.lens = target
                    redshift._state.adding = True
                    redshift.save()
                ad_col = AdminCollection.objects.create(item_type=redshifts[0]._meta.model.__name__,myitems=redshifts)
                action.send(self.owner,target=admin,verb='AddHome',level='success',action_object=ad_col)
            if generic_image_ids:
                generic_images = apps.get_model(app_label="lenses",model_name='GenericImage').objects.filter(id__in=generic_image_ids)
                for generic_image in generic_images:
                    generic_image.lens = target
                    generic_image._state.adding = True
                    generic_image.save()
                ad_col = AdminCollection.objects.create(item_type=generic_images[0]._meta.model.__name__,myitems=generic_images)
                action.send(self.owner,target=admin,verb='AddHome',level='success',action_object=ad_col)
            if imaging_ids:
                imagings = apps.get_model(app_label="lenses",model_name='Imaging').objects.filter(id__in=imaging_ids)
                for imaging in imagings:
                    imaging.lens = target
                    imaging._state.adding = True
                    imaging.save()
                ad_col = AdminCollection.objects.create(item_type=imagings[0]._meta.model.__name__,myitems=imagings)
                action.send(self.owner,target=admin,verb='AddHome',level='success',action_object=ad_col)
            if spectrum_ids:
                spectra = apps.get_model(app_label="lenses",model_name='Spectrum').objects.filter(id__in=spectrum_ids)
                for spectrum in spectra:
                    spectrum.lens = target
                    spectrum._state.adding = True
                    spectrum.save()
                ad_col = AdminCollection.objects.create(item_type=spectra[0]._meta.model.__name__,myitems=spectra)
                action.send(self.owner,target=admin,verb='AddHome',level='success',action_object=ad_col)
            


            # Second, transfer all the PRI data
            redshifts = apps.get_model(app_label="lenses",model_name='Redshift').objects.filter(lens=new).filter(access_level='PRI')
            for redshift in redshifts:
                redshift.lens = target
                redshift.save()
            generic_images = apps.get_model(app_label="lenses",model_name='GenericImage').objects.filter(lens=new).filter(access_level='PRI')
            for generic_image in generic_images:
                generic_image.lens = target
                generic_image.save()
            imagings = apps.get_model(app_label="lenses",model_name='Imaging').objects.filter(lens=new).filter(exists=True).filter(access_level='PRI')
            for imaging in imagings:
                imaging.lens = target
                imaging.save()
            spectra = apps.get_model(app_label="lenses",model_name='Spectrum').objects.filter(lens=new).filter(exists=True).filter(access_level='PRI')
            for spectrum in spectra:
                spectrum.lens = target
                spectrum.save()


            # DON'T Delete the 'new' lens here
            # It should already be PRI and should remain accessible for the owner to delete.
                


class AskPrivateAccess(ConfirmationTask):
    class Meta:
        proxy = True
        
    def allowed_responses(self):
        return ['yes','no']

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        objs_owner = self.get_all_recipients()[0]
        task_owner = self.owner
        if response == 'yes':
            objs = apps.get_model(app_label="lenses",model_name=self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            objs_owner.giveAccess(objs,task_owner) # this sends a notification as well.
        else:
            notify.send(sender=objs_owner,
                        recipient=self.owner,
                        verb='AskPrivateAccessRejectedNote',
                        level='error',
                        timestamp=timezone.now(),
                        action_object=self)


class AskToJoinGroup(ConfirmationTask):
    class Meta:
        proxy = True
        
    def allowed_responses(self):
        return ['yes','no']

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        group_owner = self.get_all_recipients()[0]
        group_id = self.cargo['object_ids'][0]
        group = SledGroup.objects.get(pk=group_id)
        if response == 'yes':
            from . import Users
            task_owner = Users.objects.filter(id=self.owner.id) # needs to be a query set
            group.addMember(group_owner,task_owner) # this sends a notification as well.
        else:
            notify.send(sender=group_owner,
                        recipient=self.owner,
                        verb='AskToJoinGroupRejectedNote',
                        level='error',
                        timestamp=timezone.now(),
                        action_object=self,
                        group_name=group.name,
                        group_url=group.get_absolute_url())


class AddData(ConfirmationTask):
    class Meta:
        proxy = True

    responses_allowed = []
    
    def allowed_responses(self):
        return self.responses_allowed

    def finalizeTask(self):
        obj_responses = self.heard_from().annotate(name=F('recipient__username')).values('response').first()
        dum = json.loads(obj_responses['response'])
        lens_ids = []
        for id in dum:
            lens_ids.append(int(id))
        
        pri = []
        pub = []
        #loop through the uploaded data objects, which we then associate with an owner (uploader)
        # and associate the uploaded image (which was stored in the temporary dir)
        for i,obj in enumerate(serializers.deserialize("json",self.cargo['objects'])):
            obj.object.owner = self.owner
            #THIS IS a bit HACKY BECAUSE THE FUNCTION IN_IDS REMOVES DUPLICATES BUT WE SOMETIMES WANT DUPLICATES, SO I GET THE LENS OBJECTS INDIVIDUALLY HERE
            lens_match = apps.get_model(app_label="lenses",model_name='Lenses').accessible_objects.in_ids(self.owner,[lens_ids[i]])[0]
  
            if not obj.object.pk:
                obj.object.lens = lens_match
                if 'image' in obj.object._meta.fields:
                    obj.object.image.name = obj.object.image.name
                if obj.object.access_level == "PRI":
                    pri.append(obj.object)
                else:
                    pub.append(obj.object)

        # Save data in the database
        # Here we don't use bulk_create. We could, but then we need to separate the uploaded data by class/model
        for datum in (pri+pub):
            datum.save()

        if pri:
            # The name of 'perm' depends on the object type
            for obj in pri:
                model_ref = pri.__class__
                perm = 'view_' + model_ref._meta.model_name
                assign_perm(perm,self.owner,obj)
        if pub:
            from . import Users
            ad_col = AdminCollection.objects.create(item_type=pub[0]._meta.model.__name__,myitems=pub)
            action.send(self.owner,target=Users.getAdmin().first(),verb='AddHome',level='success',action_object=ad_col)
        return TemplateResponse(request,'simple_message.html',context={'message':'Data successfully added to the database!'})          



class AcceptNewUser(ConfirmationTask):
    class Meta:
        proxy = True

    def allowed_responses(self):
        return ['yes','no']

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        from . import Users
        task_owner = Users.objects.get(id=self.owner.id) # needs to be a query set
        site = Site.objects.get_current()
        if response == 'yes':
            task_owner.is_active = True
            limits_ref = apps.get_model(app_label="lenses",model_name='LimitsAndRoles')
            limits_ref.objects.create(user=task_owner)
            default_storage.create_dir('temporary/'+task_owner.username)
            content = bytes('dummy text to create the user directory','utf-8')
            default_storage.put_object(content,'temporary/'+task_owner.username+'/dummy.txt')
            task_owner.save()
            action.send(self.owner,target=Users.getAdmin().first(),verb='AcceptNewUserHome',level='success',action_object=task_owner)
            subject = 'Welcome to SLED'
            html_message = get_template('emails/successful_registration.html')
            mycontext = {
                'first_name': task_owner.first_name,
                'last_name': task_owner.last_name,
                'protocol': 'http',
                'domain': site.domain,
                'user_url': task_owner.get_absolute_url(),
                'username': task_owner.username,
            }
            html_message = html_message.render(mycontext)
            plain_message = strip_tags(html_message)
        else:
            subject = 'SLED: Unsuccessful registration'
            html_message = get_template('emails/unsuccessful_registration.html')
            mycontext = {
                'first_name': task_owner.first_name,
                'last_name': task_owner.last_name,
                'response':self. heard_from().get().response_comment
            }
            html_message = html_message.render(mycontext)
            plain_message = strip_tags(html_message)

        # Send email to user with the response
        user_email = task_owner.email
        from_email = 'no-reply@%s' % site.domain
        send_mail(subject,plain_message,from_email,[user_email],html_message=html_message)
            

class InspectImages(ConfirmationTask):
    class Meta:
        proxy = True

    responses_allowed = []
    
    def allowed_responses(self):
        return self.responses_allowed

    def finalizeTask(self):
        # This is modeled after the MergeLenses task
        obj_responses = self.heard_from().annotate(name=F('recipient__username')).values('response').first()
        response = json.loads(obj_responses['response'])
        print(response)
        
        ids = set([ str(id) for id in self.cargo['object_ids'] ])
        excluded = set(response["rejected"].keys())

        if response["response"] != 'None':
            to_make_public = ids.difference(excluded)
            qset = apps.get_model(app_label="lenses",model_name=self.cargo['object_type']).objects.filter(pk__in=to_make_public)
            if qset.count() > 0:
                self.owner.makePublic(qset)


### END: Confirmation task specific code
################################################################################################################################################
