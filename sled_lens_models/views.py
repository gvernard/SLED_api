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

class LensModelCreateView(BSModalCreateView):
    model = LensModels #must correspond to a class in the models.py file
    template_name = 'sled_lens_models/lens_model_create.html' #this links to the associated template html file
    form_class = LensModelCreateFormModal


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
    
    #add form valid and invalid filters

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

        