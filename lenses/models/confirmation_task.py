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
from actstream import action

import abc
import json
import os

from . import SingleObject, Collection, SledGroup






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
            notify.send(sender=admin,
                        recipient=self.owner,
                        verb='Your request to delete public objects was accepted.',
                        level='success',
                        timestamp=timezone.now(),
                        note_type='DeleteObjects',
                        object_type=self._meta.model.__name__,
                        object_ids=[self.id])
        else:
            notify.send(sender=admin,
                        recipient=self.owner,
                        verb='Your request to delete public objects was rejected.',
                        level='error',
                        timestamp=timezone.now(),
                        note_type='DeleteObjects',
                        object_type=self._meta.model.__name__,
                        object_ids=[self.id])

            
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
            object_type = self.cargo['object_type']
            model_ref = apps.get_model(app_label="lenses",model_name=object_type)
            objs = model_ref.objects.filter(pk__in=self.cargo['object_ids'])
            objs.update(owner=heir)
            pri = []
            for obj in objs:
                if object_type != 'SledGroup':
                    action.send(self.owner,
                                target=obj,
                                verb="Changed owner from %s to %s" % (self.owner,heir),
                                level='success',
                                action_type='CedeOwnership')
                if obj.access_level == 'PRI':
                    pri.append(obj)

            # Handle private objects
            if pri:
                perm = 'view_' + model_ref._meta.db_table
                assign_perm(perm,heir,pri) # don't forget to assign view permission to the new owner for the private lenses

                if object_type != 'SledGroup':
                    # Notify users with access
                    users_with_access,accessible_objects = heir.accessible_per_other(pri,'users')
                    for i,user in enumerate(users_with_access):
                        obj_ids = []
                        for j in accessible_objects[i]:
                            obj_ids.append(pri[j].id)
                        if len(obj_ids) > 1:
                            myverb = '%d private %s you have access to changed owner.' % (len(obj_ids),model_ref._meta.verbose_name_plural.title())
                        else:
                            myverb = '%d private %s you have access to changed owner.' % (len(obj_ids),model_ref._meta.verbose_name.title())    
                        notify.send(sender=self.owner,
                                    recipient=user,
                                    verb=myverb,
                                    level='info',
                                    timestamp=timezone.now(),
                                    note_type='CedeOwnership',
                                    object_type=object_type,
                                    object_ids=obj_ids)
                        
                    # Notify groups with access
                    groups_with_access,accessible_objects = heir.accessible_per_other(pri,'groups')
                    id_list = [g.id for g in groups_with_access]
                    gwa = SledGroup.objects.filter(id__in=id_list) # Needed to cast Group to SledGroup
                    for i,group in enumerate(groups_with_access):
                        obj_ids = []
                        for j in accessible_objects[i]:
                            obj_ids.append(pri[j].id)
                        if len(obj_ids) > 1:
                            myverb = '%d private %s the group has access to changed owner.' % (len(obj_ids),model_ref._meta.verbose_name_plural.title())
                        else:
                            myverb = '%d private %s the group has access to changed owner.' % (len(obj_ids),model_ref._meta.verbose_name.title())    
                        action.send(self.owner,
                                    target=gwa[i],
                                    verb=myverb,
                                    level='info',
                                    action_type='CedeOwnership',
                                    object_type=object_type,
                                    object_ids=obj_ids)

            # Handle groups
            if object_type == 'SledGroup':
                # Notify group members
                myverb='The group has changed owner from %s to %s.' % (self.owner,heir)
                action.send(self.owner,
                            target=objs[0],
                            verb=myverb,
                            level='info',
                            action_type='CedeOwnership')
                
            # Confirm to the previous owner
            notify.send(sender=heir,
                        recipient=self.owner,
                        verb='Your CedeOwnership request was accepted.',
                        level='success',
                        timestamp=timezone.now(),
                        note_type='CedeOwnership',
                        object_type=self._meta.model.__name__,
                        object_ids=[self.id])

        else:
            notify.send(sender=heir,
                        recipient=self.owner,
                        verb='Your CedeOwnership request was rejected.',
                        level='error',
                        timestamp=timezone.now(),
                        note_type='CedeOwnership',
                        object_type=self._meta.model.__name__,
                        object_ids=[self.id])

        
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
        model_ref = apps.get_model(app_label="lenses",model_name=self.cargo['object_type'])
        if len(self.cargo['object_ids']) > 1:
            myverb = 'Your request to make %d %s private was ' % (len(objs),model_ref._meta.verbose_name_plural.title())
        else:
            myverb = 'Your request to make %d %s private was ' % (len(objs),model_ref._meta.verbose_name.title())
        if response == 'yes':
            #cargo = json.loads(self.cargo)
            #objs = getattr(lenses.models,self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            objs = model_ref.objects.filter(pk__in=self.cargo['object_ids'])
            objs.update(access_level='PRI')
            perm = "view_"+objs[0]._meta.db_table
            assign_perm(perm,self.owner,objs) # don't forget to assign view permission to the new owner for the private lenses
            notify.send(sender=admin,
                        recipient=self.owner,
                        verb=myverb + ' accepted.',
                        level='success',
                        timestamp=timezone.now(),
                        note_type='MakePrivate',
                        object_type=self._meta.model.__name__,
                        object_ids=[self.id])
        else:
            notify.send(sender=admin,
                        recipient=self.owner,
                        verb=myverb + ' rejected.',
                        level='error',
                        timestamp=timezone.now(),
                        note_type='MakePrivate',
                        object_type=self._meta.model.__name__,
                        object_ids=[self.id])
        

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
            lenses = []
            for i,obj in enumerate(serializers.deserialize("json",self.cargo['objects'])):
                if i not in reject_indices:
                    obj.object.owner = self.owner
                    obj.object.create_name()
                    if not obj.object.pk:
                        obj.object.mugshot.name = 'temporary/' + self.owner.username + '/' + obj.object.mugshot.name
                    lenses.append(obj.object)
                else:
                    # Remove uploaded image
                    if not obj.object.pk:
                        os.remove(settings.MEDIA_ROOT+'/temporary/' + self.owner.username + '/' + obj.object.mugshot.name)

            # Save lenses in the database
            db_vendor = connection.vendor
            if db_vendor == 'sqlite':
                pri = []
                pub = []
                for lens in lenses:
                    lens.save()
                    if lens.access_level == 'PRI':
                        pri.append(lens)
                    else:
                        pub.append(lens)
                if pri:
                    assign_perm('view_lenses',self.owner,pri)
                if len(pub) > 0:
                    if mode == 'update':
                        atype = 'Update'
                        if len(pub) > 1:
                            myverb = '%d Lenses were updated.' % len(pub)
                        else:
                            myverb = '1 Lens was updated.'
                    else:
                        atype = 'Add'    
                        if len(pub) > 1:
                            myverb = '%d new Lenses were added.' % len(pub)
                        else:
                            myverb = '1 new Lens was added.'
                    from . import Users
                    admin = Users.objects.get(username='admin')
                    action.send(self.owner,
                                target=admin,
                                verb=myverb,
                                level='success',
                                action_type=atype,
                                object_type='Lenses',
                                object_ids=[obj.id for obj in pub])
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
        # Nlenses = len(lenses)
        # mycollection = Collection(owner=self.owner,
        #                           name="Added "+str(Nlenses)+" lenses",
        #                           access_level='PRI',
        #                           description=str(Nlenses) + " added on the " + str(timezone.now().date()),
        #                           item_type="Lenses")
        # mycollection.save()
        # mycollection.myitems = lenses
        # mycollection.save()


class AskPrivateAccess(ConfirmationTask):
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
        objs_owner = self.get_all_recipients()[0]
        task_owner = self.owner
        if response == 'yes':
            objs = apps.get_model(app_label="lenses",model_name=self.cargo['object_type']).objects.filter(pk__in=self.cargo['object_ids'])
            objs_owner.giveAccess(objs,task_owner) # this sends a notification as well.
        else:
            if len(self.cargo['object_ids']) > 1:
                myverb = 'Your request to access %d private %s was rejected.' % (len(self.cargo['object_ids']),model_ref._meta.verbose_name_plural.title())
            else:
                myverb = 'Your request to access %d private %s was rejected.' % (len(self.cargo['object_ids']),model_ref._meta.verbose_name.title())         
            notify.send(sender=objs_owner,
                        recipient=self.owner,
                        verb=myverb,
                        level='error',
                        timestamp=timezone.now(),
                        note_type='AskPrivateAccess',
                        object_type=self._meta.model.__name__,
                        object_ids=[self.id])


class AskToJoinGroup(ConfirmationTask):
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
                        verb='Your request to join group %s was rejected.' % group.name,
                        level='error',
                        timestamp=timezone.now(),
                        note_type='AskToJoinGroup',
                        object_type=self._meta.model.__name__,
                        object_ids=[self.id])

### END: Confirmation task specific code
################################################################################################################################################
