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

import lenses
from lenses.models import Imaging


# Create your views here.
@method_decorator(login_required,name='dispatch')
class ImagingDetailView(BSModalReadView):
    model = Imaging
    template_name = 'sled_data/imaging_detail.html'
    context_object_name = 'imaging'

    def get_queryset(self):
        return self.model.accessible_objects.all(self.request.user)
