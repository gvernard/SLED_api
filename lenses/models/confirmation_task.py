from django.db import models,connection
from django.utils import timezone
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core import serializers
from django.urls import reverse
from django import forms
from django.db.models import Q,F,Count
from django.apps import apps
from django.conf import settings

from guardian.shortcuts import assign_perm


from notifications.signals import notify

import abc
import json
import os

from . import SingleObject, Collection






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
        ('ResolveDuplicates','Resolve duplicate objects')
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
        verbose_name = "confirmation_task"
        verbose_name_plural = "confirmation_tasks"
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
        return reverse('confirmation:single_task',kwargs={'task_id':self.id})

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
        subject = 'A %s task requires your response' % self.task_type
        message = 'Dear %s user, there is a %s task that requires your response. Click here for details: %s/confirmation/single/%s' % (site.name,self.task_type,site.domain,self.id)
        recipient_emails = list(users.values_list('email',flat=True))
        from_email = 'manager@%s' % site.domain
        #send_mail(subject,message,from_email,recipient_emails)
        
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

    # To be overwritten by the proxy models
    #@abc.abstractmethod
    def getForm(self):
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
        
    class myForm(forms.Form):
        mychoices = [('yes','Yes'),('no','No')]
        response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
        response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

    def allowed_responses(self):
        return ['yes','no']

    def getForm(self):
        return self.myForm()

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        from . import Users
        admin = Users.getAdmin().first()
        if response == 'yes':
            #cargo = json.loads(self.cargo)
            #getattr(.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids']).delete()
            apps.get_model(app_label="lenses",model_name=self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids']).delete()
            notify.send(sender=admin,recipient=self.owner,verb='Your request to delete public objects was accepted',level='success',timestamp=timezone.now(),note_type='DeleteObjects',task_id=self.id)
        else:
            notify.send(sender=admin,recipient=self.owner,verb='Your request to delete public objects was rejected',level='error',timestamp=timezone.now(),note_type='DeleteObjects',task_id=self.id)

            
class CedeOwnership(ConfirmationTask):
    class Meta:
        proxy = True

    class myForm(forms.Form):
        mychoices = [('yes','Yes'),('no','No')]
        response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
        response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

    def allowed_responses(self):
        return ['yes','no']

    def getForm(self):
        return self.myForm()

    def finalizeTask(self,**kwargs):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        heir = self.get_all_recipients()[0]
        if response == 'yes':
            #cargo = json.loads(self.cargo)
            #objs = getattr(lenses.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            objs = apps.get_model(app_label="lenses",model_name=self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            objs.update(owner=heir)
            pri = []
            for lens in objs:
                if lens.access_level == 'PRI':
                    pri.append(lens)
            if pri:
                assign_perm('view_lenses',heir,pri) # don't forget to assign view permission to the new owner for the private lenses
            notify.send(sender=heir,recipient=self.owner,verb='Your CedeOwnership request was accepted',level='success',timestamp=timezone.now(),note_type='CedeOwnership',task_id=self.id)
            notify.send(sender=heir,recipient=heir,verb='You have accepted a CedeOwnership request',level='success',timestamp=timezone.now(),note_type='CedeOwnership',task_id=self.id)
        else:
            notify.send(sender=heir,recipient=self.owner,verb='Your CedeOwnership request was rejected',level='error',timestamp=timezone.now(),note_type='CedeOwnership',task_id=self.id)

        
class MakePrivate(ConfirmationTask):
    class Meta:
        proxy = True
        
    class myForm(forms.Form):
        mychoices = [('yes','Yes'),('no','No')]
        response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
        response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

    def allowed_responses(self):
        return ['yes','no']

    def getForm(self):
        return self.myForm()

    def finalizeTask(self):
        # Here, only one recipient to get a response from
        response = self.heard_from().get().response
        from . import Users
        admin = Users.getAdmin().first()
        if response == 'yes':
            #cargo = json.loads(self.cargo)
            #objs = getattr(lenses.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            objs = apps.get_model(app_label="lenses",model_name=self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            objs.update(access_level='PRI')
            assign_perm('view_lenses',self.owner,objs) # don't forget to assign view permission to the new owner for the private lenses
            notify.send(sender=admin,recipient=self.owner,verb='Your request to make objects private was accepted',level='success',timestamp=timezone.now(),note_type='MakePrivate',task_id=self.id)
        else:
            notify.send(sender=admin,recipient=self.owner,verb='Your request to make objects private was rejected',level='error',timestamp=timezone.now(),note_type='MakePrivate',task_id=self.id)
        

class ResolveDuplicates(ConfirmationTask):
    class Meta:
        proxy = True

    responses_allowed = []
    
    class myForm(forms.Form):
        pass
    
    def allowed_responses(self):
        return self.responses_allowed

    def getForm(self):
        return self.myForm()

    def finalizeTask(self):
        # First find the lenses that where selected as duplicates (to be rejected)
        obj_responses = self.heard_from().annotate(name=F('recipient__username')).values('response').first()
        responses = json.loads(obj_responses['response'])
        reject_indices = []
        for response in responses:
            if response['insert'] == 'no':
                reject_indices.append(int(response['index']))
        #print(reject_indices)

        # Second, keep only those lenses marked for saving
        lenses = []
        for i,obj in enumerate(serializers.deserialize("json",self.cargo)):
            if i not in reject_indices: 
                obj.object.owner = self.owner
                obj.object.create_name()
                obj.object.mugshot.name = 'temporary/' + self.owner.username + '/' + obj.object.mugshot.name
                lenses.append(obj.object)
            else:
                # Remove uploaded image
                os.remove(settings.MEDIA_ROOT+'/temporary/' + self.owner.username + '/' + obj.object.mugshot.name)

        # Save lenses in the database
        db_vendor = connection.vendor
        if db_vendor == 'sqlite':
            pri = []
            for lens in lenses:
                lens.save()
                if lens.access_level == 'PRI':
                    pri.append(lens)
            if pri:
                assign_perm('view_lenses',self.owner,pri)
        else:
            lenses = Lenses.objects.bulk_create(lenses)
            # Here I need to upload and rename the images accordingly.
            pri = []
            for lens in lenses:
                if lens.access_level == 'PRI':
                    pri.append(lens)
            if pri:
                assign_perm('view_lenses',self.owner,pri)
        
        #  Create a collection
        mycollection = Collection(owner=self.owner,name="Worst",access_level='PRI',description="Aliens invaded earth in 2019 in the form of a virus.",item_type="Lenses")
        mycollection.save()
        mycollection.myitems = lenses
        mycollection.save()
        
### END: Confirmation task specific code
################################################################################################################################################
