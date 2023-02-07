from django.shortcuts import redirect
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

from guardian.shortcuts import get_objects_for_user, get_objects_for_group, get_users_with_perms, get_groups_with_perms

from bootstrap_modal_forms.generic import (
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
class CollectionSplitListView(TemplateView):
    model = Collection
    allow_empty = True
    template_name = 'sled_collections/collection_split_list.html'
    paginate_by = 10  # if pagination is desired

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qset_owned = Collection.accessible_objects.owned(self.request.user)
        context['collections_owned'] = qset_owned
        context['collections_access'] = Collection.accessible_objects.all(self.request.user).filter(access_level='PRI').filter(~Q(owner=self.request.user))
        context['collections_search'] = Collection.accessible_objects.all(self.request.user).filter(access_level='PUB').filter(~Q(owner=self.request.user))[:10]
        context['form'] = CollectionSearchForm()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        form = CollectionSearchForm(data=request.POST)
        if form.is_valid():
            search_term = form.cleaned_data['search_term']
            if not search_term:
                collections = Collection.objects.none()
            else:
                context['form'] = form
                collections = Collection.objects.filter(access_level='PUB').exclude(owner=request.user).filter(name__icontains=search_term)
            context['collections_search'] = collections
        return self.render_to_response(context)

    
@method_decorator(login_required,name='dispatch')
class CollectionDetailView(DetailView):
    model = Collection
    template_name = 'sled_collections/collection_detail.html'

    def get_queryset(self):
        return Collection.accessible_objects.all(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection'] = self.object
        context['accessible_items'] = self.object.getSpecificModelInstances(self.request.user)
        return context
       

#=============================================================================================================================
### BEGIN: Modal views
#=============================================================================================================================       
@method_decorator(login_required,name='dispatch')
class CollectionCreateView(BSModalCreateView):
    template_name = 'sled_collections/collection_create.html'
    form_class = CollectionCreateForm
    success_url = reverse_lazy('sled_collections:collections-list')

    def get_initial(self):
        ids = self.request.GET.getlist('ids')
        ids_str = ','.join(ids)
        item_type = self.kwargs['obj_type']
        return {'ids': ids_str,'item_type':item_type}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids = self.request.GET.getlist('ids')
        ids_str = ','.join(ids)
        obj_model = apps.get_model(app_label='lenses',model_name=self.kwargs['obj_type'])
        context['items'] = obj_model.accessible_objects.in_ids(self.request.user,ids)
        return context

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            ids = form.cleaned_data['ids'].split(',')
            obj_model = apps.get_model(app_label='lenses',model_name=self.kwargs['obj_type'])
            items = obj_model.accessible_objects.in_ids(self.request.user,ids)
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            access_level = form.cleaned_data['access_level']
            mycollection = Collection(owner=self.request.user,name=name,access_level=access_level,description=description,item_type=self.kwargs['obj_type'])
            mycollection.save()
            mycollection.myitems = items
            mycollection.save()
            messages.add_message(self.request,messages.SUCCESS,"Collection <b>"+name+"</b> was successfully created!")
            return HttpResponseRedirect(reverse('sled_collections:collections-detail',kwargs={'pk':mycollection.id})) 
        else:
            response = super().form_valid(form)
            return response


@method_decorator(login_required,name='dispatch')
class CollectionAskAccessView(BSModalUpdateView): # It would be a BSModalFormView, but the update view pass the object id automatically
    model = Collection
    template_name = 'sled_collections/collection_ask_access.html'
    form_class = CollectionAskAccessForm

    def get_queryset(self):
        return Collection.accessible_objects.all(self.request.user)

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            col = self.get_object()
            owners_ids = col.ask_access_for_private(self.request.user)
            for username in owners_ids.keys():
                cargo = {'object_type':col.item_type,'object_ids': owners_ids[username],'comment':form.cleaned_data['justification']}
                receiver = Users.objects.filter(username=username) # receiver must be a queryset
                mytask = ConfirmationTask.create_task(self.request.user,receiver,'AskPrivateAccess',cargo)
            messages.add_message(self.request,messages.WARNING,"Owners of private objects in the collection have been notified about your request.")
        response = super().form_valid(form)
        return response


@method_decorator(login_required,name='dispatch')
class CollectionDeleteView(BSModalDeleteView):
    model = Collection
    template_name = 'sled_collections/collection_delete.html'
    success_message = 'Success: Collection was deleted.'
    success_url = reverse_lazy('sled_collections:collections-list')
    
    def get_queryset(self):
        return Collection.accessible_objects.owned(self.request.user)

    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        return super().delete(*args, **kwargs)

    
@method_decorator(login_required,name='dispatch')
class CollectionUpdateView(BSModalUpdateView):
    model = Collection
    template_name = 'sled_collections/collection_update.html'
    form_class = CollectionUpdateForm
    success_message = 'Success: Collection was updated.'
    
    def get_queryset(self):
        return Collection.accessible_objects.owned(self.request.user)


@method_decorator(login_required,name='dispatch')
class CollectionGiveRevokeAccessView(BSModalUpdateView): # It would be a BSModalFormView, but the update view pass the object id automatically
    model = Collection
    template_name = 'sled_collections/collection_give_revoke_access.html'
    form_class = CollectionGiveRevokeAccessForm

    def get_queryset(self):
        return Collection.accessible_objects.owned(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'mode':self.kwargs.get('mode')})
        return kwargs

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
                    ug_message.append('Users: %s' % (','.join(["<b>"+user.username+"</b>" for user in users])))
                if len(groups) > 0:
                    ug_message.append('Groups: %s' % (','.join(["<b>"+group.name+"</b>" for group in groups])))
                message = "Access to the collection given to %s" % ' and '.join(ug_message)
                messages.add_message(self.request,messages.SUCCESS,message)
            elif mode == 'revoke':
                self.request.user.revokeAccess(collection,target_users)
                ug_message = []
                if len(users) > 0:
                    ug_message.append('Users: %s' % (','.join(["<b>"+user.username+"</b>" for user in users])))
                if len(groups) > 0:
                    ug_message.append('Groups: %s' % (','.join(["<b>"+group.name+"</b>" for group in groups])))
                message = "Access to the collection revoked from %s" % ' and '.join(ug_message)
                messages.add_message(self.request,messages.SUCCESS,message)
            else:
                messages.add_message(self.request,messages.ERROR,"Unknown action! Can either be <b>give</b> or <b>revoke</b>.")
        response = super().form_valid(form)
        return response

    
@method_decorator(login_required,name='dispatch')
class CollectionAddItemsView(BSModalFormView):
    template_name = 'sled_collections/collection_select_to_add_items.html'
    form_class = CollectionAddItemsForm
    success_message = 'Success: Items added to collection.'
    success_url = reverse_lazy('lenses:lens-query')
    
    def get_initial(self):
        ids = self.request.GET.getlist('ids')
        ids_str = ','.join(ids)
        return {'ids': ids_str}
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'obj_type': self.kwargs['obj_type']})
        return kwargs
    
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            obj_model = apps.get_model(app_label='lenses',model_name=self.kwargs['obj_type'])
            ids = form.cleaned_data['ids'].split(',')
            to_add = obj_model.accessible_objects.in_ids(self.request.user,ids)
            col = form.cleaned_data['target_collection']
            res = col.addItems(self.request.user,to_add)
            if res['status'] != "ok":
                message = "Error: "
                return TemplateResponse(request,'simple_message.html',context={'message':message})
            else:
                N_private = to_add.filter(access_level='PRI').count()
                N_public = to_add.count() - N_private
                if N_private>0 and N_public>0:
                    msg = "<b>"+str(N_public)+"</b> public and <b>"+str(N_private)+"</b> private "+obj_model._meta.verbose_name_plural.title()+" added to the collection."
                elif N_public>0:
                    if N_public>1:
                        msg = "<b>"+str(N_public)+"</b> public "+obj_model._meta.verbose_name_plural.title()+" added to the collection."
                    else:
                        msg = "<b>"+str(N_public)+"</b> public "+obj_model._meta.verbose_name.title()+" added to the collection."
                else:
                    if N_private>1:
                        msg = "<b>"+str(N_private)+"</b> private "+obj_model._meta.verbose_name_plural.title()+" added to the collection."
                    else:
                        msg = "<b>"+str(N_private)+"</b> private "+obj_model._meta.verbose_name.title()+" added to the collection."
                messages.add_message(self.request,messages.SUCCESS,msg)
                return HttpResponseRedirect(reverse('sled_collections:collections-detail',kwargs={'pk':col.id}))
        else:
            response = super().form_valid(form)
            return response

@method_decorator(login_required,name='dispatch')
class CollectionRemoveItemsView(BSModalUpdateView):
    model = Collection
    template_name = 'sled_collections/collection_remove_items.html'
    form_class = CollectionRemoveItemsForm

    def get_queryset(self):
        return Collection.accessible_objects.owned(self.request.user)

    def get_initial(self):
        ids = self.request.GET.getlist('ids')
        ids_str = ','.join(ids)
        return {'ids': ids_str}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids = self.request.GET.getlist('ids')
        obj_model = apps.get_model(app_label='lenses',model_name=self.object.item_type)
        qset_items = obj_model.accessible_objects.in_ids(self.request.user,ids)
        context['items_to_remove'] = qset_items
        return context

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            col = self.get_object()
            ids = form.cleaned_data['ids'].split(',')
            obj_model = apps.get_model(app_label='lenses',model_name=col.item_type)
            to_remove = obj_model.accessible_objects.in_ids(self.request.user,ids)
            res = col.removeItems(self.request.user,to_remove)
            if res['status'] != "ok":
                message = "Error: "
                return TemplateResponse(request,'simple_message.html',context={'message':message})
            else:
                if res["N_removed"] == 1:
                    msg = "<b>" + str(res["N_removed"]) + " " + obj_model._meta.verbose_name.title() + "</b> removed from the collection."
                else:
                    msg = "<b>" + str(res["N_removed"]) + " " + obj_model._meta.verbose_name_plural.title() + "</b> removed from the collection."
                messages.add_message(self.request,messages.SUCCESS,msg)
                return HttpResponseRedirect(reverse('sled_collections:collections-detail',kwargs={'pk':col.id})) 
        else:
            response = super().form_valid(form)
            return response


@method_decorator(login_required,name='dispatch')
class CollectionMakePublicView(BSModalUpdateView):
    model = Collection
    template_name = 'sled_collections/collection_make_public.html'
    form_class = CollectionMakePublicForm

    def get_queryset(self):
        return Collection.accessible_objects.owned(self.request.user)  

    def form_valid(self,form):
        # I need to call the below line first because it resets the access_level back to private (probably because there is no 'proper' update taking place)
        response = super().form_valid(form)
        if not is_ajax(self.request.META):
            col = self.get_object()
            messages.add_message(self.request,messages.SUCCESS,"Collection is now public!")
            # Post to the collection's activity stream
            qset = Collection.accessible_objects.filter(id=col.id)
            self.request.user.makePublic(qset)

        return response


@method_decorator(login_required,name='dispatch')
class CollectionCedeOwnershipView(BSModalUpdateView):
    model = Collection
    template_name = 'sled_collections/collection_cede_ownership.html'
    form_class = CollectionCedeOwnershipForm

    def get_queryset(self):
        return Collection.accessible_objects.owned(self.request.user)
    
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            col = self.get_object()
            heir = form.cleaned_data['heir']
            heir = Users.objects.filter(id=heir.id)
            heir_dict = heir.values('first_name','last_name')[0]
            justification = form.cleaned_data['justification']
            self.request.user.cedeOwnership(col,heir,justification)        
            message = "User <b>"+heir[0].username+"</b> has been notified about your request."
            messages.add_message(self.request,messages.WARNING,message)
            return redirect('sled_collections:collections-list')
        else:
            response = super().form_valid(form)
            return response


@method_decorator(login_required,name='dispatch')
class CollectionViewAccessView(BSModalReadView):
    model = Collection
    template_name = 'sled_collections/collection_view_access.html'

    def get_queryset(self):
        return Collection.accessible_objects.owned(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection'] = self.object
        
        users = self.object.getUsersWithAccessNoOwner()
        N_no_access = []
        names_no_access = []
        for user in users:
            no_acc = self.object.getNoAccess(user)
            N_no_access.append(len(no_acc))
            names = [obj.name for obj in no_acc]
            names_no_access.append( ','.join(names) )
        context['u_no_access'] = zip(users,N_no_access,names_no_access)

        groups = self.object.getGroupsWithAccessNoOwner()
        obj_model = apps.get_model(app_label='lenses',model_name=self.object.item_type)
        perm = 'view_' + obj_model._meta.db_table
        all_priv = self.object.getSpecificModelInstances(self.object.owner).filter(access_level='PRI')
        N_no_access = []
        names_no_access = []
        for group in groups:
            acc = get_objects_for_group(group,perm,klass = all_priv)
            #no_acc = all_priv.order_by().difference(acc.order_by())
            no_acc = list( set(all_priv) - set(acc) )
            N_no_access.append(len(no_acc))
            names = [obj.name for obj in no_acc]
            names_no_access.append( ','.join(names) )
        context['g_no_access'] = zip(groups,N_no_access,names_no_access)        
        
        return context

#=============================================================================================================================
### END: Modal views
#=============================================================================================================================       
