from django.shortcuts import render,redirect
from django.http import HttpResponse,HttpResponseRedirect
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.db.models import F,Q,Count
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, DetailView, ListView
from django.urls import reverse,reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.utils import is_ajax

import lenses
from lenses.models import Users, ConfirmationTask
from urllib.parse import urlparse

from .forms import *


@method_decorator(login_required,name='dispatch')
class TaskListView(ListView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_list.html'
    context_object_name = 'owner'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.kwargs.get('admin'):
            admin = Users.getAdmin().first()
            owner = self.model.accessible_objects.owned(admin)
            recipient = self.model.custom_manager.all_as_recipient(admin)
        else:
            owner = self.model.accessible_objects.owned(self.request.user).exclude(task_type__exact='AcceptNewUser')
            recipient = self.model.custom_manager.all_as_recipient(self.request.user)

        o_paginator = Paginator(owner,50)
        o_page_number = self.request.GET.get('tasks_owned-page',1)

        r_paginator = Paginator(recipient,50)
        r_page_number = self.request.GET.get('tasks_recipient-page',1)
        if 'admin' in self.kwargs.keys():
            admin_page = True
        else:
            admin_page = False

        context = {'N_owner': o_paginator.count,
                   'owner_range': o_paginator.page_range,
                   'owner': o_paginator.get_page(o_page_number),
                   'N_recipient': r_paginator.count,
                   'recipient_range': r_paginator.page_range,
                   'recipient': r_paginator.get_page(r_page_number),
                   'admin_page': admin_page
                   }
        return context


@method_decorator(login_required,name='dispatch')
class TaskDetailOwnerView(BSModalReadView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_detail_owner.html'
    context_object_name = 'task'

    def get_queryset(self):
        if self.kwargs.get('admin'):
            return self.model.accessible_objects.owned(Users.getAdmin().first())
        else:
            return self.model.accessible_objects.owned(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allowed'] = ' or '.join( self.object.allowed_responses() )
        context['hf'] = self.object.heard_from().annotate(name=F('recipient__username')).values('name','response','created_at','response_comment')
        context['nhf'] = self.object.not_heard_from().values_list('recipient__username',flat=True)
        return context

    
@method_decorator(login_required,name='dispatch')
class TaskDetailRecipientView(BSModalFormView):
    template_name = 'sled_tasks/task_detail_recipient.html'
    success_message = 'Success: Your response has been recorded.'
    success_url = reverse_lazy('sled_tasks:tasks-list')
    task = None
    
    def get_initial(self):
        # Check if a response is already in the database  
        print(self.kwargs)
        try:
            if self.kwargs.get('admin'):
                print('admin in kwargs')
                db_response = self.task.recipients.through.objects.get(confirmation_task__exact=self.task.id,recipient__username=Users.getAdmin().first().username)
            else:
                db_response = self.task.recipients.through.objects.get(confirmation_task__exact=self.task.id,recipient__username=self.request.user.username)
        except task.DoesNotExist:
            db_response = None
        initial = {}
        if db_response.response:
            initial['response'] = db_response.response
            if db_response.response_comment:
                initial['response_comment'] = db_response.response_comment
        return initial
       
    def get_form_class(self):
        task_id = self.kwargs['pk']
        if self.kwargs.get('admin'):
            self.task = ConfirmationTask.custom_manager.all_as_recipient(Users.getAdmin().first()).get(id=task_id)
        else:
            self.task = ConfirmationTask.custom_manager.all_as_recipient(self.request.user).get(id=task_id)
        if self.task.task_type == "CedeOwnership":
            return CedeOwnershipForm
        elif self.task.task_type == "MakePrivate":
            return MakePrivateForm
        elif self.task.task_type == "DeleteObject":
            return DeleteObjectForm
        elif self.task.task_type == "AskPrivateAccess":
            return AskPrivateAccessForm
        elif self.task.task_type == "AskToJoinGroup":
            return AskToJoinGroupForm
        elif self.task.task_type == "AcceptNewUser":
            return AcceptNewUserForm
        else:
            pass
        
    def get_form(self,form_class=None):
        form = super().get_form(form_class)
        if 'response' in form.initial:
            form.fields["response"].disabled = True
        if 'response_comment' in form.initial:
            form.fields["response_comment"].disabled = True        
        return form 
    
    def get_context_data(self, **kwargs):
        print('get context data')
        print(self.kwargs)
        context = super(TaskDetailRecipientView,self).get_context_data(**kwargs)

        context['task'] = self.task
        
        # Comment from task sender
        comment = ''
        if 'comment' in self.task.cargo:
            comment = self.task.cargo['comment']
        context['comment'] = comment

        # Queryset of objects in the task
        objects = getattr(lenses.models,self.task.cargo["object_type"]).objects.filter(pk__in=self.task.cargo["object_ids"])
        context['objects'] = objects

        # Object type (singular or plural) for the objects in the task
        if objects.count() > 1:
            object_type = getattr(lenses.models,self.task.cargo["object_type"])._meta.verbose_name_plural.title()
        else:
            object_type = getattr(lenses.models,self.task.cargo["object_type"])._meta.verbose_name.title()
        context['object_type'] = object_type
        #context['admin'] = self.kwargs.get('admin')
        try:
            if self.kwargs.get('admin'):
                db_response = self.task.recipients.through.objects.get(confirmation_task__exact=self.task.id,recipient__username=Users.getAdmin().first().username)
            else:
                db_response = self.task.recipients.through.objects.get(confirmation_task__exact=self.task.id,recipient__username=self.request.user.username)
        except task.DoesNotExist:
            db_response = None
        context['db_response'] = db_response
        
        return context

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            response = self.request.POST.get('response')
            response_comment = self.request.POST.get('response_comment')
            messages.add_message(self.request,messages.SUCCESS,self.success_message)
            if self.kwargs.get('admin'):
                self.task.registerAndCheck(Users.getAdmin().first(),response,response_comment)
                return HttpResponseRedirect(reverse('sled_tasks:tasks-list-admin'))
            else:
                self.task.registerAndCheck(self.request.user,response,response_comment)
                return HttpResponseRedirect(reverse('sled_tasks:tasks-list'))
        else:
            return super(TaskDetailRecipientView,self).form_valid(form)
