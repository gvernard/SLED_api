from django.shortcuts import render,redirect
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.db.models import F,Q,Count
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, DetailView, ListView
from django.urls import reverse,reverse_lazy

import lenses
from lenses.models import Users, ConfirmationTask
from urllib.parse import urlparse


@method_decorator(login_required,name='dispatch')
class TaskListView(ListView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_list.html'
    context_object_name = 'owner'
    
    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recipient'] = self.model.custom_manager.all_as_recipient(self.request.user)
        return context


@method_decorator(login_required,name='dispatch')
class TaskDetailOwnerView(DetailView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_detail_owner.html'
    context_object_name = 'task'

    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allowed'] = ' or '.join( self.object.allowed_responses() )
        context['hf'] = self.object.heard_from().annotate(name=F('recipient__username')).values('name','response','created_at','response_comment')
        context['nhf'] = self.object.not_heard_from().values_list('recipient__username',flat=True)
        return context


@method_decorator(login_required,name='dispatch')
class TaskDetailRecipientView(DetailView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_detail_recipient.html'
    context_object_name = 'task'

    def get_queryset(self):
        return self.model.custom_manager.all_as_recipient(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Comment from task sender
        comment = ''
        if 'comment' in self.object.cargo:
            comment = self.object.cargo['comment']
        context['comment'] = comment

        # Queryset of objects in the task
        objects = getattr(lenses.models,self.object.cargo["object_type"]).objects.filter(pk__in=self.object.cargo["object_ids"])
        context['objects'] = objects

        # Object type (singular or plural) for the objects in the task
        if objects.count() > 1:
            object_type = getattr(lenses.models,self.object.cargo["object_type"])._meta.verbose_name_plural.title()
        else:
            object_type = getattr(lenses.models,self.object.cargo["object_type"])._meta.verbose_name.title()
        context['object_type'] = object_type

        # Check if a response is already in the database
        
        try:
            db_response = self.object.recipients.through.objects.get(confirmation_task__exact=self.object.id,recipient__username=self.request.user.username)
        except self.object.DoesNotExist:
            db_response = None
        context['db_response'] = db_response

        # Form to display, prepopulate and disable if response exists 
        form = self.object.getForm()
        if db_response.response:
            form.fields["response"].initial = db_response.response
            form.fields["response"].disabled = True
            if db_response.response_comment:
                form.fields["response_comment"].initial = db_response.response_comment
                form.fields["response_comment"].disabled = True
        context['form'] = form
        
        return context
                
    def post(self, *args, **kwargs):
        referer = urlparse(self.request.META['HTTP_REFERER']).path
        if referer == self.request.path:
            response = self.request.POST.get('response')
            response_comment = self.request.POST.get('response_comment')
            task_id = self.request.POST.get('task_id')
            task = ConfirmationTask.objects.get(pk=task_id)
            task.registerAndCheck(self.request.user,response,response_comment)
            #return redirect(reverse('sled_tasks:tasks-detail-recipient',kwargs={'pk':task_id}))
            return HttpResponseRedirect(self.request.path_info)
        else:
            message = "Not authorized action!"
            return TemplateResponse(request,'simple_message.html',context={'message':message})

        
