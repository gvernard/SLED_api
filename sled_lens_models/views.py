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
from django import forms
from django.core.exceptions import ValidationError




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
from lenses.models import Collection, Lenses, ConfirmationTask, LensModels
from urllib.parse import urlparse
from random import randint
import csv
import os 
import tarfile 
import tempfile
from pathlib import Path
import numpy
import coolest
from coolest.api.analysis import Analysis
from coolest.api.plotting import ModelPlotter, MultiModelPlotter, ParametersPlotter
from coolest.api import util
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LogNorm, TwoSlopeNorm
import io
import base64

'''class LensModelSplitListView():'''


class LensModelDetailView(DetailView):
    model = LensModels
    template_name = 'sled_lens_models/lens_model_detail.html'
    context_object_name = 'lens_model'  #getting all lens models

    def get_queryset(self):
        return LensModels.accessible_objects.all(self.request.user)  #match model



    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lens_model = self.get_object()        
        context.update({
            'lensing_entities': lens_model.lensing_entities,
            'source_light_model': lens_model.source_light_model,
            'r_eff': lens_model.r_eff_source,
            'einstein_radius': lens_model.einstein_radius,
            'free_parameters': lens_model.free_parameters
        })
        return context






    

    #def get_template_names(self):
    #    model_name = self.kwargs.get('model')
    #    return ['sled_lens_models/lens_model_detail.html']
    #    #grab the correct template from the templates folder

    #def get_context_data(self, **kwargs):
        #context = super().get_context_data(**kwargs)
        #lens_model = context['lens']

        # Only get models for THIS lens
        #context['lens'] = lens.lens_models.order_by('-date_created')  # uses related_name from ForeignKey
        #context['lens_models'] = lens.lens_models.all()  # uses related_name from ForeignKey
        #return context
    



class test(CreateView):
    model = Lenses
    template_name = 'sled_lens_models/test.html'
    context_object_name = 'test'
    test = 'hi does this work?'
    #return test
    #test.html must go inside of the templates folder in my app (move from lens directory)

def print_info(coolest_object):
    source_index = 2  # index of the source galaxy in the list of `lensing entities`
    print("Lensing entities:", [type(le).__name__ for le in coolest_object.lensing_entities])
    print("Source light model:", [type(m).__name__ for m in coolest_object.lensing_entities[source_index].light_model])
    #from COOLEST website - prints name of lensing entities and source light model 

class LensModelCreateView(BSModalCreateView):
    model = LensModels #must correspond to a class in the models.py file
    template_name = 'sled_lens_models/lens_model_create.html' #this links to the associated template html file
    form_class = LensModelCreateFormModal


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lens_models'] = LensModels.objects.filter(lens=self.object)
        return context
        form_class = LensModelCreateForm

    def get_template_names(self):
        model_name = self.kwargs.get('model')
        return ['sled_lens_models/lens_model_create.html']
        #grab the correct template from the templates folder

    def get_initial(self):
        owner = self.request.user
        lens = Lenses.objects.get(id=self.kwargs.get('lens'))
        return {'owner': owner, 'lens': lens}
        #populates certain fields automatically (user and lens in question)
    
    def get_form_kwargs(self):
        kwargs = super(LensModelCreateView,self).get_form_kwargs() #LensModelsCreateView is from the view.py folder and is a class
        kwargs['user'] = self.request.user
        return kwargs
        #when searching back for this lens, when finding its kwargs (which is information about it stored in a database), it can also find a user being the person who added the model
   
    


    
    def form_invalid(self, form):
        print("invalid return form")
        return super().form_invalid(form)
        
    def form_valid(self, form):
        form.instance.owner = self.request.user
        self.object = form.save()  # <-- This sets self.object
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.lens:
            return reverse('lenses:lens-detail', kwargs={'pk': self.object.lens.id})
        return reverse('sled_lens_models:lens-model-detail', kwargs={'pk': self.object.pk})
        
        
    #     def get_queryset(self):
    #     #note: self allows the user to modify this specific lens not all lenses
    #     model = apps.get_model(app_label='lenses', model_name=self.kwargs.get('model'))
    #     return model.accessible_objects.owned(self.request.user)
    #     #returns queryset based on what the editor can view (can be helpful for access level) (only needed when looking up existing set not creating new)

    #     def get_form_class(self):
    #     model_name = self.kwargs.get('model')
    #     return forms.LensModelCreateFormModal
    #     #displays the form to the user



        #uncomment when success message is displayed
    
    #add a success message function when ready

#class LensModelUpdate(BSModalUpdateView):

        
