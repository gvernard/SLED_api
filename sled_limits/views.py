from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse,reverse_lazy

from bootstrap_modal_forms.generic import (
    BSModalUpdateView,
    BSModalReadView,
)
from bootstrap_modal_forms.mixins import is_ajax

from lenses.models import Users, LimitsAndRoles, ConfirmationTask
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

    def get_initial(self):
        initial = {
            'active': self.get_object().user.is_active
        }
        return initial
        
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            # Reassigning admin tasks
            if 'is_admin' in form.changed_data and not form.cleaned_data["is_admin"]:
                new_admin = Users.selectRandomAdmin(exclude_usernames=[self.object.user.username]).get().username
                admin = Users.getAdmin().first()
                tasks = ConfirmationTask.custom_manager.pending_for_user(admin).filter(cargo__user_admin=self.object.user.username)
                for task in tasks:
                    task.cargo['user_admin'] = new_admin
                    task.save()

            # Make user active
            if 'active' in form.changed_data:
                target_user = self.get_object()
                target_user.user.is_active = form.cleaned_data["active"]
                target_user.user.save(update_fields=["is_active"])
                
        response = super().form_valid(form)
        return response
        
    def get_success_url(self):
        return reverse('sled_users:user-visit-card',kwargs={'username':self.object.user.username})

    def get_success_message(self):
        return self.success_message % dict(username=self.object.user.username)
