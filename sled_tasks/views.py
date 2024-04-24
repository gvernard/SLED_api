from django.shortcuts import render,redirect
from django.http import HttpResponse,HttpResponseRedirect
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.db.models import F,Q,Count
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.generic import TemplateView, DetailView, ListView
from django.urls import reverse,reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from django.forms import formset_factory

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.mixins import is_ajax

import lenses
from lenses.models import Users, ConfirmationTask, Lenses, Redshift, Imaging, Spectrum, GenericImage
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
            #owner = self.model.accessible_objects.owned(self.request.user).exclude(task_type__exact='AcceptNewUser')
            #recipient = self.model.custom_manager.all_as_recipient(self.request.user).exclude(task_type__exact='ResolveDuplicates')
            owner_only = self.model.custom_manager.all_as_owner_only(self.request.user).exclude(task_type__exact='AcceptNewUser')
            recipient_only = self.model.custom_manager.all_as_recipient_only(self.request.user)
            both = self.model.custom_manager.both_owner_recipient(self.request.user)
            owner = owner_only|both.filter(status="C")
            recipient = recipient_only|both.filter(status="P")
            

        date_check = timezone.now() - timezone.timedelta(days=10)
        N_old = owner.filter( Q(status='C') & Q(modified_at__lt=date_check) ).count()
        print(date_check,N_old)
        
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
                   'admin_page': admin_page,
                   'N_old': N_old
                   }
        return context

    def get(self, *args, **kwargs):
        if self.kwargs.get('admin') and not self.request.user.limitsandroles.is_admin:
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
        task = self.object
        
        context['allowed'] = ' or '.join( map(str.upper,task.allowed_responses()) )

        # Queryset of objects in the task
        objects = getattr(lenses.models,task.cargo["object_type"]).objects.filter(pk__in=task.cargo["object_ids"])
        context['objects'] = objects

        # Object type (singular or plural) for the objects in the task
        if objects.count() > 1:
            object_type = getattr(lenses.models,task.cargo["object_type"])._meta.verbose_name_plural.title()
        else:
            object_type = getattr(lenses.models,task.cargo["object_type"])._meta.verbose_name.title()
        context['object_type'] = object_type

        #context['hf'] = self.object.heard_from().annotate(name=F('recipient__username')).values('name','response','created_at','response_comment')
        #context['nhf'] = self.object.not_heard_from().values_list('recipient__username',flat=True)
        context['responses'] = task.get_all_responses().annotate(name=F('recipient__username')).values('name','response','created_at','response_comment')
        return context


@method_decorator(login_required,name='dispatch')
class TaskInspectDetailOwnerView(BSModalReadView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_detail_inspect_owner.html'
    context_object_name = 'task'

    def get_queryset(self):
        qset1 = self.model.custom_manager.completed_for_user(self.request.user)
        qset2 = self.model.custom_manager.pending_for_user(self.request.user)
        return qset1|qset2

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        
        # Queryset of objects in the task
        objects = getattr(lenses.models,task.cargo["object_type"]).objects.filter(pk__in=task.cargo["object_ids"])
        context['objects'] = objects

        # Object type (singular or plural) for the objects in the task
        if objects.count() > 1:
            object_type = getattr(lenses.models,task.cargo["object_type"])._meta.verbose_name_plural.title()
        else:
            object_type = getattr(lenses.models,task.cargo["object_type"])._meta.verbose_name.title()
        context['object_type'] = object_type

        context['responses'] = task.get_all_responses().annotate(name=F('recipient__username')).values('name','response','created_at','response_comment')
        return context

    
    
    
@method_decorator(login_required,name='dispatch')
class TaskMergeDetailOwnerView(BSModalReadView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_detail_merge_owner.html'
    context_object_name = 'task'

    def get_queryset(self):
        qset1 = self.model.custom_manager.completed_for_user(self.request.user)
        qset2 = self.model.custom_manager.pending_for_user(self.request.user)
        return qset1|qset2

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Queryset of objects in the task
        existing_lens = getattr(lenses.models,self.object.cargo["object_type"]).objects.get(pk=self.object.cargo["existing_lens"])
        context['existing_lens'] = existing_lens
        new_lens = getattr(lenses.models,self.object.cargo["object_type"]).objects.get(pk=self.object.cargo["new_lens"])
        context['new_lens'] = new_lens

        #context['hf'] = self.object.heard_from().annotate(name=F('recipient__username')).values('name','response','created_at','response_comment')
        #context['nhf'] = self.object.not_heard_from().values_list('recipient__username',flat=True)
        responses = list(self.object.get_all_responses().annotate(name=F('recipient__username')).values('name','response','created_at','response_comment'))
        context['response'] = {}
        if responses[0]['response'] == '':
            context['response']['response'] = ''
            context['response']['name'] = responses[0]['name']
        else:
            response = json.loads(responses[0]['response'])
            context['response']['response'] = response['response']
            context['response']['response_comment'] = response['response_comment']
            context['response']['name'] = responses[0]['name']
            context['response']['created_at'] = responses[0]['created_at']

            context['response']['fields'] = []
            context['response']['items'] = {}
            items = response['items']
            # Queryset of merged objects
            for item in items:
                object_type = item.split('-')[0]
                if object_type != 'Field':
                    model_ref = getattr(lenses.models,object_type)
                    object_id = item.split('-')[1]
                    try:
                        myobject = model_ref.objects.get(id=object_id)
                    except model_ref.DoesNotExist:
                        pass
                    else:
                        #final_obj_label = myobject.__str__().split('-')[1:]
                        final_obj_label = myobject
                
                        if object_type not in context['response']['items']:
                            context['response']['items'][object_type] = []
                        context['response']['items'][object_type].append(final_obj_label)
                else:
                    field_name = item.split('-')[1]
                    verbose_name = getattr(lenses.models,'Lenses')._meta.get_field(field_name).verbose_name
                    context['response']['fields'].append(verbose_name)

            # Object type (singular or plural) for the objects in the task
            new_items = {}
            keys = context['response']['items'].keys()
            for key in keys:
                if len(context['response']['items'][key]) > 1:
                    new_key = getattr(lenses.models,key)._meta.verbose_name_plural.title()
                else:
                    new_key = getattr(lenses.models,key)._meta.verbose_name.title()
                new_items[new_key] = context['response']['items'][key]
            context['response']['items'] = new_items
                    
                
        return context


@method_decorator(login_required,name='dispatch')
class TaskResolveDuplicatesCompleteDetailView(BSModalReadView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_detail_complete_resolve_duplicates.html'
    context_object_name = 'task'

    def get_queryset(self):
        return self.model.custom_manager.completed_for_user(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mode = self.object.cargo["mode"]
        ras = []
        decs = []
        cargo_objects = json.loads(self.object.cargo["objects"])

        for i in range(0,len(cargo_objects)):
            ras.append( cargo_objects[i]["fields"]["ra"] )
            decs.append( cargo_objects[i]["fields"]["dec"] )

        response = self.object.get_all_responses().values('response','created_at').first()
        context["responded_at"] = response["created_at"]
        
        choices = [None]*len(ras)
        insert_dict = json.loads(response["response"])
        for i in range(0,len(insert_dict)):
            index = int(insert_dict[i]["index"])
            choice = insert_dict[i]["insert"]
            if choice == "no":
                choices[index] = 'no'
            elif choice == "yes":
                choices[index] = 'yes'
            else:
                choices[index] = 'merge'

        context["responses"] = zip(ras,decs,choices)
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
        generic_images = GenericImage.objects.filter(lens=new).filter(access_level='PUB')
    
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
            'generic_images': generic_images,
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
        if context['generic_images']:
            for generic_image in context['generic_images']:
                choices.append( 'GenericImage-'+str(generic_image.pk) )
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


        
@method_decorator(login_required,name='dispatch')
class TaskInspectDetailView(TemplateView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_inspect_detail.html'
    context_object_name = 'task'


    def get(self, request, *args, **kwargs):
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        object_type = task.cargo["object_type"]
        objects = getattr(lenses.models,object_type).objects.filter(pk__in=task.cargo["object_ids"])
        initial = []
        if object_type == "Lenses":
            for lens in objects:
                dum = {}
                dum["obj_id"] = lens.id
                dum["name"] = lens.name
                dum["image_url"] = lens.mugshot.url
                initial.append(dum)
        elif object_type == "Imaging":
            pass
        elif object_type == "Spectrum":
            pass
        elif object_type == "GenericImage":
            pass
        else:
            # PROBLEM
            pass

        ImagesFormSet = formset_factory(InspectImagesBaseForm,extra=0)
        formset = ImagesFormSet(initial=initial)
        
        context = {}
        context['formset'] = formset
        context['final_form'] = InspectImagesForm()
        context['task'] = task
        return self.render_to_response(context)


    def post(self, request, *args, **kwargs):
        referer = urlparse(request.META['HTTP_REFERER']).path
        task_id = self.kwargs['pk']
        try:
            task = ConfirmationTask.objects.get(pk=task_id)
        except ConfirmationTask.DoesNotExist:
            return TemplateResponse(request,'simple_message.html',context={'message':'This task does not exist.'})

        if referer == request.path:
            ImagesFormSet = formset_factory(InspectImagesBaseForm,extra=0)
            formset = ImagesFormSet(data=request.POST)
            if formset.is_valid():
                rejected = []
                for form in formset.cleaned_data:
                    if form["rejected"]:
                        dum = {}
                        dum["id"] = form["obj_id"]
                        dum["comment"] = form["comment"]
                        rejected.append(dum)

                form = InspectImagesForm(data=request.POST,N_rejected=len(rejected))

                if form.is_valid():
                    # Hack to pass the insert_form responses to the task
                    #my_response = json.dumps(myform.cleaned_data)
                    #task.responses_allowed = [my_response]
                    #task.registerAndCheck(request.user,my_response,myform.cleaned_data['response_comment'])
                    #return TemplateResponse(request,'simple_message.html',context={'message':'You have responded successfully to this task.'})
                    print('mapa')
                else:
                    context = {}
                    context['formset'] = formset
                    context['final_form'] = form
                    context['task'] = task
                    return self.render_to_response(context)
            else:
                form = InspectImagesForm(data=request.POST)
                context = {}
                context['formset'] = formset
                context['final_form'] = form
                context['task'] = task
                return self.render_to_response(context)
            return self.render_to_response(context)
        else:
            return TemplateResponse(request,'simple_message.html',context={'message':'You are not authorized to view this page.'})

    
    
@method_decorator(login_required,name='dispatch')
class TaskDeleteView(BSModalDeleteView):
    model = ConfirmationTask
    template_name = 'sled_tasks/task_delete.html'
    success_message = 'Success: Task was deleted.'
    context_object_name = 'task'
    success_url = reverse_lazy('sled_tasks:tasks-list')

    def get_queryset(self):
        return self.model.objects.filter( Q(owner=self.request.user) and Q(status='C') )
