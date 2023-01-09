from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import ListView

from bootstrap_modal_forms.generic import (
    BSModalFormView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.utils import is_ajax

from lenses.models import Users, Band
from .forms import *

from django.contrib.admin.views.decorators import staff_member_required

@method_decorator(staff_member_required,name='dispatch')
class BandListView(ListView):
    model = Band
    allow_empty = True
    template_name = 'sled_band/band_list.html'
    paginate_by = 10  # if pagination is desired

    def get_queryset(self):
        return Band.objects.all().order_by('wavelength')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bands'] = self.object_list
        return context


@method_decorator(login_required,name='dispatch')
class BandCreateView(BSModalFormView):
    model = Band
    template_name = 'sled_band/band_create.html'
    form_class = BandCreateForm
    success_url = reverse_lazy('sled_band:band-list')

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


@method_decorator(login_required,name='dispatch')
class BandUpdateView(BSModalUpdateView):
    model = Band
    template_name = 'sled_band/band_update.html'
    form_class = BandUpdateForm
    success_message = 'Success: band was updated.'
    success_url = reverse_lazy('sled_band:band-list')




@method_decorator(login_required,name='dispatch')
class BandDeleteView(BSModalDeleteView):
    model = Band
    template_name = 'sled_band/band_delete.html'
    success_message = 'Success: band was deleted.'
    success_url = reverse_lazy('sled_band:band-list')
    context_object_name = 'band'


