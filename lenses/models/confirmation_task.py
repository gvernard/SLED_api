from django.db import models,connection
from django.utils import timezone
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core import serializers
from django.urls import reverse
from django import forms
from django.db.models import Q,F,Count,CharField
from django.apps import apps
from django.conf import settings
from django.template.loader import get_template
from django.template import Context

from guardian.shortcuts import assign_perm

from notifications.signals import notify
from actstream import action

import abc
import json
import os

from . import Lenses, SingleObject, Collection, SledGroup, AdminCollection



class ConfirmationTaskManager(models.Manager):
    def pending_for_user(self,user):
        return super().get_queryset().filter(status='P').filter(Q(owner=user)|Q(recipients__username=user.username))

    def completed_for_user(self,user):
        return super().get_queryset().filter(status='C').filter(Q(owner=user)|Q(recipients__username=user.username))

    def all_as_recipient(self,user):
        return super().get_queryset().filter(Q(recipients__username=user.username))

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
        ('AskPrivateAccess','Ask access to private objects'),
        ('AskToJoinGroup','Request to add to group'),
        ('AddData','Associate data to lens.'),
        ('AcceptNewUser','Accept new user'),
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
        task.inviteRecipients(task.recipients)
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
            mycontext = Context({
                'first_name': user.first_name,
                'task_type': self.task_type,
                'task_url': self.get_absolute_url()
            })
            message = html_message.render(mycontext)
            recipient_email = user.email
            send_mail(subject,message,from_email,recipient_emails)



        
    def get_all_recipients(self):
        """
        Gets all the recipients of the confirmation task. 
         
        Returns:
            A QuerySet with User objects.
        """
        return self.recipients.all()

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
    response = models.CharField(max_length=100, help_text="The response of a given user to a given confirmation task.") 
    response_comment = models.CharField(max_length=100, help_text="A comment (optional) from the recipient on the given response.") 

class DeleteObject(ConfirmationTask):
    class Meta:
        proxy = True
        
    def allowed_responses(self):
        return ['yes','no']

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        from . import Users
        admin = Users.getAdmin().first()
        if response == 'yes':
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
            objs.update(owner=heir)
            pri = []
            pub = []
            for obj in objs:
                if obj.access_level == 'PRI':
                    pri.append(obj)
                else:
                    pub.append(obj)

            # Handle public objects
            if pub and object_type != 'SledGroup':
                from . import Users
                ad_col = AdminCollection.objects.create(item_type=object_type,myitems=pub)
                action.send(self.owner,target=Users.getAdmin().first(),verb='CedeOwnershipHome',level='info',action_object=ad_col,previous_id=self.owner.id,next_id=heir.id)
                    
            # Handle private objects
            if pri:
                perm = 'view_' + model_ref._meta.db_table
                assign_perm(perm,heir,pri) # don't forget to assign view permission to the new owner for the private lenses

                if object_type != 'SledGroup':
                    # Notify users with access
                    users_with_access,accessible_objects = heir.accessible_per_other(pri,'users')
                    for i,user in enumerate(users_with_access):
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

            perm = "view_"+objs[0]._meta.db_table
            assign_perm(perm,self.owner,objs) # don't forget to assign view permission to the owner for the private lenses
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

            # Finally update the objects' access_level to private
            objs.update(access_level='PRI')                    

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
        responses = json.loads(obj_responses['response'])
        reject_indices = []
        for response in responses:
            if response['insert'] == 'no':
                reject_indices.append(int(response['index']))
        #print(reject_indices)

        mode = self.cargo['mode']
        
        if mode == "makePublic":
            ids = []
            for i,obj in enumerate(serializers.deserialize("json",self.cargo['objects'])):
                if i not in reject_indices:
                    ids.append(obj.object.pk)
            lenses = apps.get_model(app_label="lenses",model_name='Lenses').accessible_objects.in_ids(self.owner,ids)
            output = self.owner.makePublic(lenses)
        else:
            # Keep only lenses marked to save
            pri = []
            pub = []
            for i,obj in enumerate(serializers.deserialize("json",self.cargo['objects'])):
                if i not in reject_indices:
                    obj.object.owner = self.owner
                    #obj.object.create_name() #commented out because we need for old lenses this name
                    if not obj.object.pk:
                        obj.object.mugshot.name = 'temporary/' + self.owner.username + '/' + obj.object.mugshot.name
                    if obj.object.access_level == 'PRI':
                        pri.append(obj.object)
                    else:
                        pub.append(obj.object)
                else:
                    # Remove uploaded image
                    if not obj.object.pk:
                        os.remove(settings.MEDIA_ROOT+'/temporary/' + self.owner.username + '/' + obj.object.mugshot.name)

            # Insert in the database
            for lens in (pri+pub):
                lens.save()

            if pri:
                assign_perm('view_lenses',request.user,pri)
            if pub:
                # Main activity stream for public lenses
                from . import Users
                ad_col = AdminCollection.objects.create(item_type="Lenses",myitems=pub)
                action.send(self.owner,target=Users.getAdmin().first(),verb='AddHome',level='success',action_object=ad_col)
            return TemplateResponse(request,'simple_message.html',context={'message':'Duplicates resolved successfully!'})

        
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
                    obj.object.image.name = 'temporary/' + self.owner.username + '/' + obj.object.image.name
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
                perm = 'view_' + model_ref._meta.db_table
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
        if response == 'yes':
            task_owner.is_active = True
            task_owner.save()
            action.send(self.owner,target=Users.getAdmin().first(),verb='AcceptNewUserHome',level='success',action_object=task_owner)
            subject = 'Welcome to SLED'
            html_message = get_template('emails/successful_registration.html')
            mycontext = Context({
                'first_name': task_owner.first_name,
                'last_name': task_owner.last_name,
                'user_url': task_owner.get_absolute_url(),
                'username': task_owner.username,
            })
            message = html_message.render(mycontext)
        else:
            subject = 'SLED: Unsuccessful registration'
            html_message = get_template('emails/unsuccessful_registration.html')
            mycontext = Context({
                'first_name': task_owner.first_name,
                'last_name': task_owner.last_name,
                'response':self. heard_from().get().response_comment
            })
            message = html_message.render(mycontext)
            

        # Send email to user with the response
        site = Site.objects.get_current()
        user_email = task_owner.email
        from_email = 'no-reply@%s' % site.domain
        send_mail(subject,message,from_email,user_email)            
            
### END: Confirmation task specific code
################################################################################################################################################
