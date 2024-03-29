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
from lenses.models import Users, ConfirmationTask, Lenses, Redshift, Imaging, Spectrum
from urllib.parse import urlparse
import json

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

    def get(self, *args, **kwargs):
        if self.kwargs.get('admin') and not self.request.user.is_staff:
            return TemplateResponse(self.request,'simple_message.html',context={'message':'You are not authorized to view this page.'})
        return super(TaskListView,self).get(*args, **kwargs)

    
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
        try:
            if self.kwargs.get('admin'):
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


@method_decorator(login_required,name='dispatch')
class TaskMergeDetailView(TemplateView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_merge_detail.html'
    context_object_name = 'task'

    def get_context(self,new,target):
        redshifts = Redshift.objects.filter(lens=new).filter(access_level='PUB')
        imagings = Imaging.objects.filter(lens=new).filter(exists=True).filter(access_level='PUB')
        spectra = Spectrum.objects.filter(lens=new).filter(exists=True).filter(access_level='PUB')
    
        # Get different lens fields
        fields = {}
        target_fields,new_fields = target.compare(new)
        for key,val in target_fields.items():
            if new_fields[key]:
                fields[key] = {
                    "existing": val,
                    "new": new_fields[key]
                }
            
        context = {
            'target': target,
            'new': new,
            'redshifts': redshifts,
            'imagings': imagings,
            'spectra': spectra,
            'fields': fields
        }
        return context

    def get_allowed_choices(self,context):
        choices = []
        if context['redshifts']:
            for redshift in context['redshifts']:
                choices.append( 'Redshift-'+str(redshift.pk) )
        if context['imagings']:
            for imaging in context['imagings']:
                choices.append( 'Imaging-'+str(imaging.pk) )
        if context['spectra']:
            for spectrum in context['spectra']:
                choices.append( 'Spectrum-'+str(spectrum.pk) )
        if context['fields']:
            for key,field in context['fields'].items():
                choices.append( 'Field-'+key )
        return choices

        
    def get(self, request, *args, **kwargs):
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        target = Lenses.objects.get(id=task.cargo["existing_lens"])
        new = Lenses.objects.get(id=task.cargo["new_lens"])
        
        if request.user == task.owner:
            return TemplateResponse(request,'simple_message.html',context={'message':'You initiated a merge.'})
        else:
            context = self.get_context(new,target)
            choices = self.get_allowed_choices(context)
            context['form'] = MergeLensesForm(choices=choices)
            context['task'] = task
            return self.render_to_response(context)


    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if not task:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if referer == request.path:
            target = Lenses.objects.get(id=task.cargo["existing_lens"])
            new = Lenses.objects.get(id=task.cargo["new_lens"])
            context = self.get_context(new,target)
            choices = self.get_allowed_choices(context)
            myform = MergeLensesForm(data=request.POST,choices=choices)
            
            if myform.is_valid():
                # Hack to pass the insert_form responses to the task
                my_response = json.dumps(myform.cleaned_data)
                task.responses_allowed = [my_response]
                task.registerAndCheck(request.user,my_response,myform.cleaned_data['response_comment'])
                return TemplateResponse(request,'simple_message.html',context={'message':'You have responded successfully to this task.'})
            else:
                context['form'] = myform
                context['task'] = task
                return self.render_to_response(context)
        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'You are not authorized to view this page.'})
