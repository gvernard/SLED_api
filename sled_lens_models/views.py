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

@method_decorator(login_required,name='dispatch')
class test(BSModalCreateView):
    template_name = 'sled_lens_models/lens_model_create.html'
    form_class = LensModelCreateFormModal
    #context_object_name = 'test'
    #test = 'hi does this work?'
    #return test


        
