from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse,reverse_lazy

from bootstrap_modal_forms.generic import (
    BSModalUpdateView,
    BSModalReadView,
)

from lenses.models import Users, LimitsAndRoles
from .forms import *

# Create your views here.
@method_decorator(login_required,name='dispatch')
class LimitsAndRolesUpdateView(BSModalUpdateView):
    model = LimitsAndRoles
    template_name = 'sled_limits/limits_and_roles_update.html'
    form_class = LimitsAndRolesUpdateForm
    success_message = 'Success: Limits and Roles were updated for user %(username)s'
    success_url = reverse_lazy('index')

    def get_queryset(self):
        if self.request.user.limitsandroles.is_super_admin:
            return LimitsAndRoles.objects.all()
        else:
            return LimitsAndRoles.objects.none()

    def get_success_url(self):
        return reverse('sled_users:user-visit-card',kwargs={'username':self.object.user.username})

    def get_success_message(self,cleaned_data):
        return self.success_message % dict(username=self.object.user.username)
