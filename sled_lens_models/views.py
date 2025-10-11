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
from django.core.files import File
from django.core.files.storage import default_storage
from django.conf import settings
from django.http import FileResponse
from django.utils import timesince,timezone

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

import time
from datetime import timedelta
import requests



def check_image_at_url(image_url):
    """
    Checks if an image exists at the given URL by performing a HEAD request.
    Returns True if the URL points to an image, False otherwise.
    """
    image_formats = ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp")
    try:
        response = requests.head(image_url, timeout=5)  # Add a timeout to prevent hanging
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print(response.headers["Content-Type"])
        if "Content-Type" in response.headers and response.headers["Content-Type"] in image_formats:
            return True
    except requests.exceptions.RequestException:
        # Handle network errors, timeouts, or invalid URLs
        pass
    return False



class LensModelDetailView(DetailView):
    model = LensModels
    template_name = 'sled_lens_models/lens_model_detail.html'
    context_object_name = 'lens_model'

    def get_queryset(self):
        return LensModels.accessible_objects.all(self.request.user)  #match model

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lens_model = self.get_object()

        

        #####################################
        ### NOTE: The following checks should be replaced by properly querying the status of the Celery task that is generating the plots

        most_recent = max(lens_model.created_at,lens_model.modified_at)
        time_too_long = ((most_recent + timedelta(hours=1)) < timezone.now())

        check_dmr = lens_model.dmr_plot_exists()
        check_corner = lens_model.corner_plot_exists()
        
        if check_dmr:
            context.update({
                'dmr_flag': True,
                'dmr_message': '',
                'dmr_plot_url': lens_model.get_dmr_plot_url()
            })
        else:
            if time_too_long:
                # More than an hour has passed
                context.update({
                    'dmr_flag': False,
                    'dmr_message': 'There was an error generating the plot, please contact the admins.',
                    'dmr_plot_url': ''
                })
            else:
                # Less than an hour has passed
                context.update({
                    'dmr_flag': False,
                    'dmr_message': 'The Data-Model-Residual-Source plot is being generated. Please check again in a few minutes.',
                    'dmr_plot_url': ''
                })
                
        if check_corner:
            context.update({
                'corner_flag': True,
                'corner_message': '',
                'corner_plot_url': lens_model.get_corner_plot_url()
            })
        else:
            if time_too_long:
                # More than an hour has passed
                context.update({
                    'corner_flag': False,
                    'corner_message': 'There was an error generating the plot, please contact the admins.',
                    'corner_plot_url': ''
                })
            else:
                # Less than an hour has passed
                context.update({
                    'corner_flag': False,
                    'corner_message': 'The corner plot is being generated. Please check again in a few minutes.',
                    'corner_plot_url': ''
                })        
        #####################################

        return context
    


class LensModelCreateView(BSModalCreateView):
    model = LensModels #must correspond to a class in the models.py file
    template_name = 'sled_lens_models/lens_model_create.html' #this links to the associated template html file
    form_class = LensModelCreateFormModal
    success_message = 'Success: Lens Model was successfully added.'

    def get_initial(self):
        owner = self.request.user
        lens = Lenses.objects.get(id=self.kwargs.get('lens'))
        return {'owner': owner, 'lens': lens}
        #populates certain fields automatically (owner and lens in question)
    
    def get_form_kwargs(self):
        # Get the kwargs, add the user submitting the model to the kwargs, return the new kwargs
        kwargs = super(LensModelCreateView,self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
   
    def form_valid(self, form):
        self.request.FILES['coolest_file'].seek(0)        
        self.object = form.save()
        response = super(LensModelCreateView,self).form_valid(form)
        return response
    
    def get_success_url(self):
        return reverse('sled_lens_models:lens-model-detail', kwargs={'pk': self.object.id})
        
        
    #     def get_queryset(self):
    #     #note: self allows the user to modify this specific lens not all lenses
    #     model = apps.get_model(app_label='lenses', model_name=self.kwargs.get('model'))
    #     return model.accessible_objects.owned(self.request.user)
    #     #returns queryset based on what the editor can view (can be helpful for access level) (only needed when looking up existing set not creating new)



        

@method_decorator(login_required,name='dispatch')
class LensModelUpdateView(BSModalUpdateView):
    model = LensModels
    template_name = 'sled_lens_models/lens_model_update.html'
    form_class = LensModelUpdateFormModal
    success_message = 'Success: Lens Model was updated.'
    
    def get_queryset(self):
        return LensModels.accessible_objects.owned(self.request.user)

    def form_valid(self, form):
        self.request.FILES['coolest_file'].seek(0)        
        self.object = form.save()
        response = super(LensModelUpdateView,self).form_valid(form)
        return response

    def get_success_url(self):
        return reverse('sled_lens_models:lens-model-detail', kwargs={'pk': self.object.id})

    

@method_decorator(login_required,name='dispatch')
class LensModelDeleteView(BSModalDeleteView):
    model = LensModels
    template_name = 'sled_lens_models/lens_model_delete.html'
    form_class = LensModelDeleteForm
    success_message = 'Success: Lens Model was deleted.'
    #success_url = reverse_lazy('sled_lens_models:lens-list')
    
    def get_queryset(self):
        return LensModels.accessible_objects.owned(self.request.user)

    def get_form_kwargs(self):
        kwargs = super(LensModelDeleteView,self).get_form_kwargs()
        kwargs['id'] = self.get_object().id
        return kwargs

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            self.object.save()
        response = super().form_valid(form)
        return response
    
    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.get_object().lens.id})




#@method_decorator(login_required,name='dispatch')
@login_required
def LensModelDownloadView(request):
    lens_model_id = request.GET.get('lens_model_id')
    qset = LensModels.accessible_objects.in_ids(request.user,[lens_model_id])

    if qset:
        lens_model = qset[0]
        path = lens_model.coolest_file.url
        filename = path.split('/')[-1]
        response = FileResponse(open(path,'rb'))
        response['Content-Disposition'] = 'inline; filename=' + filename
        return response
    else:
        return TemplateResponse(request,'simple_message.html',context={'message':'This Lens Model does not exist.'})

