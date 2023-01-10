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

from lenses.models import Users, Instrument
from .forms import *

from django.contrib.admin.views.decorators import staff_member_required

@method_decorator(staff_member_required,name='dispatch')
class InstrumentCreateView(BSModalFormView):
    template_name = 'sled_instrument/instrument_create.html'
    form_class = InstrumentCreateForm
    success_url = reverse_lazy('sled_users:user-admin',kwargs={'hash':'instruments'})

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            name = form.cleaned_data['name']
            extended_name = form.cleaned_data['extended_name']
            info = form.cleaned_data['info']
            instrument = Instrument(name=name, extended_name=extended_name, info=info)
            instrument.save()
            messages.add_message(self.request,messages.SUCCESS,"Instrument <b>"+name+"</b> was successfully created!")
        response = super().form_valid(form)
        return response

    
@method_decorator(staff_member_required,name='dispatch')
class InstrumentUpdateView(BSModalUpdateView):
    model = Instrument
    template_name = 'sled_instrument/instrument_update.html'
    form_class = InstrumentUpdateForm
    success_message = 'Success: instrument was updated.'
    success_url = reverse_lazy('sled_users:user-admin',kwargs={'hash':'instruments'})


@method_decorator(staff_member_required,name='dispatch')
class InstrumentDeleteView(BSModalDeleteView):
    model = Instrument
    template_name = 'sled_instrument/instrument_delete.html'
    success_message = 'Success: instrument was deleted.'
    success_url = reverse_lazy('sled_users:user-admin',kwargs={'hash':'instruments'})
    context_object_name = 'instrument'


