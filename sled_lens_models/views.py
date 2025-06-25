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
import os 
import tarfile 
import tempfile
from pathlib import Path
import numpy
import coolest
from coolest.api.analysis import Analysis
from coolest.api.plotting import ModelPlotter, MultiModelPlotter
from coolest.api import util

'''class LensModelSplitListView():'''


class LensModelDetailView(DetailView):
    model = Lenses
    template_name = 'sled_lens_models/lens_model_detail.html'
    context_object_name = 'lens_model'  #getting all lens models

    def get_queryset(self):
        return LensModels.accessible_objects.all(self.request.user)  #match model
    

    def get_template_names(self):
        model_name = self.kwargs.get('model')
        return ['sled_lens_models/lens_model_detail.html']
        #grab the correct template from the templates folder

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lens = context['lens']

        # Only get models for THIS lens
        #context['lens'] = lens.lens_models.order_by('-date_created')  # uses related_name from ForeignKey
        context['lens_models'] = lens.lens_models.all()  # uses related_name from ForeignKey
        return context
    



class test(CreateView):
    model = Lenses
    template_name = 'sled_lens_models/test.html'
    context_object_name = 'test'
    test = 'hi does this work?'
    #return test
    #test.html must go inside of the templates folder in my app (move from lens directory)

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
   
    
    def validate_coolest(tar_path):
        with tempfile.TemporaryDirectory() as tmpdir:
        # Extract tar.gz contents
            with tarfile.open(tar_path, "r:gz") as tar:
                #open the tarpath and read it in (r) as a gz file
                tar.extractall(path=tmpdir)
                #extract everything in the tarfile and put it in the tmpdir
                names = tar.getnames()
                #find the names of every file in the archive, now in the temp directory

        # Find all .json files in the archive (thing files are stored in)
            json_files = [name for name in names if name.endswith('.json')]
            #says for every name in the names list, if the name ends with .json, add that name to the json_files list

        # if the file contains more than 1 .json file, return a error 
            if len(json_files) != 1:
                return False, "Archive must contain exactly one .json file"

        # Build full path to the .json file: uses Path function to define the path of the temporary directory and adds on name of the json file
            file_path = Path(tmpdir) / json_files[0]

        # Try to load with COOLEST, and if it doesn't load, return error saying it is not in the correct format
            try:
                coolest_obj = util.get_coolest_object(file_path, verbose=False)
            except Exception:
                return False, "Incorrect Format, must match COOLEST Guidelines"

            return True, None

    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        #puts the form owner as the user
        try:
            validate_coolest_file(self.object.file.path)
        #tries to validate the COOLEST format
        except ValidationError as e:
            form.add_error('file', e)
            return self.form_invalid(form)
        #If there is an error, return an error
        self.object = form.save()
        #save the file and return the valid form message
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('lenses:lens-detail', kwargs={'pk':self.kwargs.get('lens')})
        #redirects user to lens detail page after sucess form submits 
        
        
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

        
