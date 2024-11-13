from django.http import HttpResponse
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from bootstrap_modal_forms.generic import BSModalFormView,BSModalReadView
from bootstrap_modal_forms.mixins import is_ajax

from sled_core.slack_api_calls import check_slack_user
from lenses.models import Users
#from .forms import *


class HowToView(TemplateView):
    template_name = "sled_howto/howto.html"

    def get_context_data(self, **kwargs):
        context = super(HowToView,self).get_context_data(**kwargs)
        return context



'''
class SlackRegisterView(BSModalFormView):
    template_name = 'sled_howto/slack_register.html'
    form_class = SlackRegisterForm
    success_url = reverse_lazy('sled_howto:sled-howto')

    def get_initial(self):
        if self.request.user.is_authenticated:
            return {'email':self.request.user.email}
        else:
            return {}        

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            msg = "You shall receive a Slack workspace invitation shortly."
            messages.add_message(self.request,messages.WARNING,msg)
        response = super().form_valid(form)
        return response
'''

class SlackRegisterView(BSModalReadView):
    model = Users
    context_object_name = 'user'

    #def get_queryset(self):
    #    return Users.objects.filter(pk=self.request.user.pk)


    def get_template_names(self):
        if self.request.user.is_authenticated:
            errors,exists = check_slack_user(self.request.user.email)
            if exists:
                return ['sled_howto/slack_register_exists.html']
            else:
                return ['sled_howto/slack_register.html']
        else:
            return ['sled_howto/slack_register_unauthenticated.html']
    
