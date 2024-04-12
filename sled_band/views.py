from django.shortcuts import render,redirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.urls import reverse,reverse_lazy
from django.contrib import messages
from django.views.generic import ListView
from django.db.models import ProtectedError

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.mixins import is_ajax

from lenses.models import Users, Band
from .forms import *

from django.contrib.admin.views.decorators import staff_member_required


@method_decorator(staff_member_required,name='dispatch')
class BandCreateView(BSModalFormView):
    model = Band
    template_name = 'sled_band/band_create.html'
    form_class = BandCreateForm
    success_url = reverse_lazy('sled_users:user-admin',kwargs={'hash':'bands'})

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            name = form.cleaned_data['name']
            info = form.cleaned_data['info']
            wavelength = form.cleaned_data['wavelength']
            band = Band(name=name, info=info, wavelength=wavelength)
            band.save()
            messages.add_message(self.request,messages.SUCCESS,"Band <b>"+name+"</b> was successfully created!")
        response = super().form_valid(form)
        return response


@method_decorator(staff_member_required,name='dispatch')
class BandUpdateView(BSModalUpdateView):
    model = Band
    template_name = 'sled_band/band_update.html'
    form_class = BandUpdateForm
    success_message = 'Success: band was updated.'
    success_url = reverse_lazy('sled_users:user-admin',kwargs={'hash':'bands'})


@method_decorator(staff_member_required,name='dispatch')
class BandDeleteView(BSModalDeleteView):
    model = Band
    template_name = 'sled_band/band_delete.html'
    success_message = 'Success: band was deleted.'
    success_url = reverse_lazy('sled_users:user-admin',kwargs={'hash':'bands'})
    context_object_name = 'band'

    def post(self,request,*args,**kwargs):
        try:
            return self.delete(request,*args,**kwargs)
        except ProtectedError as e:
            list(messages.get_messages(request))
            messages.add_message(self.request,messages.ERROR,'Cannot delete Band <strong>%s</strong> because it is being used (protected foreign key)!' % self.object.name)
            return redirect(reverse('sled_users:user-admin',kwargs={'hash':'bands'}))
