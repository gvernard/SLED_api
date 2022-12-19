from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse,reverse_lazy
from django.contrib import messages

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalCreateView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.utils import is_ajax
from actstream import action
from dirtyfields import DirtyFieldsMixin

import lenses
from lenses.models import Imaging
from .forms import *


@method_decorator(login_required,name='dispatch')
class ImagingDetailView(BSModalReadView):
    model = Imaging
    template_name = 'sled_data/imaging_detail.html'
    context_object_name = 'imaging'

    def get_queryset(self):
        return self.model.accessible_objects.all(self.request.user)

    
@method_decorator(login_required,name='dispatch')
class ImagingDeleteView(BSModalDeleteView):
    model = Imaging
    template_name = 'sled_data/imaging_delete.html'
    success_message = 'Success: Imaging data were removed.'
    context_object_name = 'imaging'

    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def delete(self, *args, **kwargs):
        self.object = self.get_object()
        if not is_ajax(self.request.META):
            action.send(self.object.owner,target=self.object.lens,verb='RemoveData',level='success',instrument=self.object.instrument.name,band=self.object.band.name)
        return super().delete(*args, **kwargs)

    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.get_object().lens.id})

    
@method_decorator(login_required,name='dispatch')
class ImagingUpdateView(BSModalUpdateView):
    model = Imaging
    template_name = 'sled_data/imaging_update.html'
    form_class = ImagingUpdateForm
    success_message = 'Success: Imaging data were updated.'
    
    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            # Report action and dirty fields?
            dum = 1
        response = super().form_valid(form)
        return response
    
    def get_success_url(self):
        return reverse('lenses:lens-detail',kwargs={'pk':self.get_object().lens.id})
