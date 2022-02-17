from django.shortcuts import render
from django.http import HttpResponse,HttpResponseRedirect,JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic import TemplateView, DetailView, ListView
from django.utils.decorators import method_decorator
from django.apps import apps
from django.urls import reverse,reverse_lazy
from django.db.models import Q
from django.contrib import messages

from guardian.shortcuts import get_objects_for_user, get_users_with_perms, get_groups_with_perms

from bootstrap_modal_forms.generic import (
    BSModalLoginView,
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalReadView,
    BSModalDeleteView
)
from bootstrap_modal_forms.utils import is_ajax

from lenses.forms import LensQueryForm
from .forms import *
from lenses.models import Collection, Lenses, ConfirmationTask
from urllib.parse import urlparse
from random import randint


@method_decorator(login_required,name='dispatch')
class CollectionListView(ListView):
    model = Collection
    allow_empty = True
    template_name = 'sled_collections/collection_list.html'
    paginate_by = 100  # if pagination is desired
    
    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = self.object_list
        return context

    
@method_decorator(login_required,name='dispatch')
class CollectionSplitListView(TemplateView):
    model = Collection
    allow_empty = True
    template_name = 'sled_collections/collection_split_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qset_owned = Collection.accessible_objects.owned(self.request.user)
        context['collections_owned'] = qset_owned
        # qset_access = Collection.accessible_objects.filter(access_level='PRI').filter(~Q(owner=self.request.user))
        # context['collections_access'] = get_objects_for_user(self.request.user,'view_'+Collection._meta.db_table,klass=qset_access)
        context['collections_access'] = Collection.accessible_objects.all(self.request.user).filter(access_level='PRI').filter(~Q(owner=self.request.user))
        return context

    
@method_decorator(login_required,name='dispatch')
class CollectionDetailView(DetailView):
    model = Collection
    template_name = 'sled_collections/collection_detail.html'

    def get_queryset(self):
        #return self.model.accessible_objects.owned(self.request.user)
        return self.model.accessible_objects.all(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection'] = self.object
        m2m_qset = self.object.myitems.all()
        ids = list(m2m_qset.values_list('gm2m_pk',flat=True))
        obj_model = apps.get_model(app_label='lenses',model_name=self.object.item_type)
        acc_qset = obj_model.accessible_objects.in_ids(self.request.user,ids)
        context['accessible_items'] = acc_qset
        return context
        
    def post(self, *args, **kwargs):
        referer = urlparse(self.request.META['HTTP_REFERER']).path
        if referer == self.request.path:
            self.object = self.get_object()
            context = super(CollectionDetailView,self).get_context_data(**kwargs)
            collection_id = self.request.POST.get('collection_id')
            col = Collection.accessible_objects.get(pk=collection_id)
            obj_ids = self.request.POST.getlist('ids',None)
            if obj_ids:
                objects = apps.get_model(app_label='lenses',model_name=col.item_type).accessible_objects.in_ids(self.request.user,obj_ids)
                res = col.removeItems(self.request.user,objects)
                if res != "success":
                    context['error_message'] = res                
            return self.render_to_response(context)
        else:
            message = "Not authorized action!"
            return TemplateResponse(request,'simple_message.html',context={'message':message})





        
        
@method_decorator(login_required,name='dispatch')
class CollectionAskAccessView(BSModalUpdateView): # It would be a BSModalFormView, but the update view pass the object id automatically
    model = Collection
    template_name = 'sled_collections/collection_ask_access.html'
    form_class = CollectionAskAccessForm

    def get_queryset(self):
        return self.model.accessible_objects.all(self.request.user)

    def form_invalid(self,form):
        response = super().form_invalid(form)
        return response

    def form_valid(self,form):
        col = self.get_object()
        if not is_ajax(self.request.META):
            owners_ids = col.ask_access_for_private(self.request.user)
            #owners = Users.objects.filter(username__in=owners_ids.keys())
            for username in owners_ids.keys():
                cargo = {'object_type':col.item_type,'object_ids': owners_ids[username],'comment':form.cleaned_data['justification']}
                receiver = Users.objects.filter(username=username) # receiver must be a queryset
                mytask = ConfirmationTask.create_task(self.request.user,receiver,'AskPrivateAccess',cargo)
            messages.add_message(self.request,messages.SUCCESS,'Owners of private lenses in the collection have been notified about your request.')
            response = super().form_valid(form)
            return response
        else:
            response = super().form_valid(form)
            return response


    

        
        
        
@method_decorator(login_required,name='dispatch')
class CollectionDeleteView(BSModalDeleteView):
    model = Collection
    template_name = 'sled_collections/collection_delete.html'
    success_message = 'Success: Collection was deleted.'
    success_url = reverse_lazy('sled_collections:collections-list')
    
    def get_queryset(self):
        return Collection.accessible_objects.all(self.request.user)

    
@method_decorator(login_required,name='dispatch')
class CollectionUpdateView(BSModalUpdateView):
    model = Collection
    template_name = 'sled_collections/collection_update.html'
    form_class = CollectionForm2
    success_message = 'Success: Collection was updated.'
    
    def get_queryset(self):
        return Collection.accessible_objects.all(self.request.user)

    
@method_decorator(login_required,name='dispatch')
class CollectionListView2(ListView):
    model = Collection
    template_name = 'sled_collections/collection_list2.html'
    #form_class = CollectionForm2

    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = self.object_list
        return context

    
@method_decorator(login_required,name='dispatch')
class CollectionAddItemsView(DetailView):
    model = Collection

    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        col = Collection.accessible_objects.get(pk=self.object.id)
        obj_ids = self.request.POST.getlist('ids',None)
        context = super(CollectionAddItemsView,self).get_context_data(**kwargs)
        if obj_ids:
            objects = apps.get_model(app_label='lenses',model_name=col.item_type).accessible_objects.in_ids(self.request.user,obj_ids)
            res = col.addItems(self.request.user,objects)
            if res != "success":
                message = "Error: "
                return TemplateResponse(request,'simple_message.html',context={'message':message})
            else:
                return HttpResponseRedirect(reverse('sled_collections:collections-detail',kwargs={'pk':self.object.id})) 
        else:
            message = "Select some objects to add!"
            return TemplateResponse(request,'simple_message.html',context={'message':message})
        
       
@method_decorator(login_required,name='dispatch')
class CollectionCreateView(CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = "sled_collections/collection_create_form.html"
    success_url = reverse_lazy('sled_collections:collections-list')
    
    def get_form_kwargs(self):
        kwargs = super(CollectionCreateView,self).get_form_kwargs()        
        referer = urlparse(self.request.META['HTTP_REFERER']).path
        if referer == self.request.path:
            kwargs['request'] = self.request
            kwargs['obj_type'] = self.request.POST.get('obj_type')
            kwargs['ids'] = [ pk for pk in self.request.POST.getlist('myitems') if pk.isdigit() ]
            kwargs['all_items'] = self.request.POST.get('all_items')
        else:
            kwargs['request'] = self.request
            kwargs['obj_type'] = self.request.POST.get('obj_type')
            ids = [ pk for pk in self.request.POST.getlist('ids') if pk.isdigit() ]
            kwargs['ids'] = ids
            kwargs['all_items'] = ','.join(ids)
        return kwargs
        
    def form_valid(self,form):
        form.instance.owner = self.request.user
        form.instance.item_type = form.cleaned_data['obj_type']
        response = super().form_valid(form)
        self.object.myitems = form.cleaned_data['myitems']
        self.object.save()
        return response

    def form_invalid(self,form):
        return super().form_invalid(form)


@method_decorator(login_required,name='dispatch')
class CollectionAddView(TemplateView):
    model = Collection
    template_name = "sled_collections/collection_create_form.html"
    
    def get(self, request, *args, **kwargs):
        message = 'You must select which lenses to update from your <a href="{% url \'users:user-profile\' %}">User profile</a>.'
        return TemplateResponse(request,'simple_message.html',context={'message':message})

    def post(self, *args, **kwargs):
        referer = urlparse(self.request.META['HTTP_REFERER']).path

        if referer == self.request.path:
            myform = CollectionForm(data=self.request.POST,user=self.request.user)
            if myform.is_valid():
                instance = myform.save(commit=False)
                instance.owner = self.request.user
                ids = [ pk for pk in self.request.POST.getlist('myitems') if pk.isdigit() ]
                obj_type = myform.cleaned_data['obj_type']
                instance.item_type = obj_type
                instance.save()
                instance.myitems = apps.get_model(app_label='lenses',model_name=obj_type).accessible_objects.in_ids(self.request.user,ids)
                instance.save()
                return HttpResponseRedirect(reverse('sled_collections:collections-list'))
            else:
                return self.render_to_response({'form': myform})
                
        else:
            obj_type = self.request.POST.get('obj_type')
            ids = [ pk for pk in self.request.POST.getlist('ids') if pk.isdigit() ]
            data = {
                "all_items": ','.join(ids),
                "obj_type": obj_type
            }
            myform = CollectionForm(data=data,user=self.request.user)
            return self.render_to_response({'form': myform})

        
@method_decorator(login_required,name='dispatch')
class CollectionGiveRevokeAccessView(BSModalUpdateView): # It would be a BSModalFormView, but the update view pass the object id automatically
    model = Collection
    template_name = 'sled_collections/collection_give_revoke_access.html'
    form_class = CollectionGiveRevokeAccessForm

    def get_initial(self):
        collection_id = self.get_object().id
        mode = self.kwargs['mode']
        return {'mode': mode,'collection_id':collection_id}

    def get_queryset(self):
        return self.model.accessible_objects.all(self.request.user)

    def form_invalid(self,form):
        response = super().form_invalid(form)
        return response

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            collection = self.get_object()
            users = form.cleaned_data['users']
            user_ids = [u.id for u in users]
            users = Users.objects.filter(id__in=user_ids)
            groups = form.cleaned_data['groups']
            group_ids = [g.id for g in groups]
            groups = SledGroup.objects.filter(id__in=group_ids)
            target_users = list(users) + list(groups)

            mode = self.kwargs['mode']
            if mode == 'give':
                self.request.user.giveAccess(collection,target_users)
                ug_message = []
                if len(users) > 0:
                    ug_message.append('Users: %s' % (','.join([user.username for user in users])))
                if len(groups) > 0:
                    ug_message.append('Groups: <em>%s</em>' % (','.join([group.name for group in groups])))
                message = 'Access to collection given to %s' % ' and '.join(ug_message)
                messages.add_message(self.request,messages.SUCCESS,message)
            elif mode == 'revoke':
                self.request.user.revokeAccess(collection,target_users)
                ug_message = []
                if len(users) > 0:
                    ug_message.append('Users: %s' % (','.join([user.username for user in users])))
                if len(groups) > 0:
                    ug_message.append('Groups: <em>%s</em>' % (','.join([group.name for group in groups])))
                message = 'Access to collection revoked from %s' % ' and '.join(ug_message)
                messages.add_message(self.request,messages.SUCCESS,message)
            else:
                messages.add_message(self.request,messages.ERROR,'Unknown action! Can either be <em>give</em> or <em>revoke</em>.')
            response = super().form_valid(form)
            return response
        else:
            response = super().form_valid(form)
            return response
    
    def get_success_url(self):
        #return reverse_lazy('sled_groups:group-list')
        return reverse_lazy('sled_collections:collections-detail',kwargs={'pk':self.get_object().id})
