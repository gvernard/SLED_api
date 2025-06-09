from django.shortcuts import render

# Create your views here.
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
from bootstrap_modal_forms.mixins import is_ajax

from lenses.forms import LensQueryForm,DownloadForm
from lenses.query_utils import get_combined_qset
from .forms import *
from lenses.models import Collection, Lenses, ConfirmationTask
from urllib.parse import urlparse
from random import randint
import csv

'''class LensModelSplitListView():'''

class LensModelDetailView(DetailView):
    model = Lenses
    template_name = 'lenses/lens_detail.html'
    context_object_name = 'lens'

    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #add all the context it needs (?)


class test(CreateView):
    model = Lenses
    template_name = 'sled_lens_models/test.html'
    context_object_name = 'test'
    test = 'hi does this work?'
    #return test
    #test.html must go inside of the templates folder in my app (move from lens directory)

class LensModelCreateView(CreateView):
    model = Lenses
    template_name = lens_model_create.html #this links to the associated template html file
    fields = ['model_type', 'method', 'creator', 'info,'] #fields in create button template

    def form_valid(self,form):
        form.instance.creator = self.request.user
        return super().form_valid(form)


  template_name = 'sled_collections/collection_create.html'
    form_class = CollectionCreateForm
    success_url = reverse_lazy('sled_collections:collections-list')

    def get_initial(self):
        ids = self.request.GET.getlist('ids')
        if not ids:
            ids = get_combined_qset(self.request.GET,self.request.user)
        ids_str = ','.join(ids)
        item_type = self.kwargs['obj_type']
        return {'ids': ids_str,'item_type':item_type}

    def get_form_kwargs(self):
        kwargs = super(CollectionCreateView,self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
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

        