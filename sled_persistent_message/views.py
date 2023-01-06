from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import ListView
from django.utils import timezone
from django.db.models import Q

from bootstrap_modal_forms.generic import (
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalCreateView,
)
from bootstrap_modal_forms.utils import is_ajax

from lenses.models import PersistentMessage
from .forms import *


@method_decorator(staff_member_required,name='dispatch')
class PersistentMessageListView(ListView):
    model = PersistentMessage
    allow_empty = True
    template_name = 'sled_persistent_message/message_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context['valid_messages'] = PersistentMessage.timeline.current() | PersistentMessage.timeline.future()
        context['past_messages'] = PersistentMessage.timeline.past()
        return context


@method_decorator(staff_member_required,name='dispatch')
class PersistentMessageCreateView(BSModalCreateView):
    model = PersistentMessage
    template_name = 'sled_persistent_message/message_create.html'
    form_class = PersistentMessageCreateUpdateForm
    success_message = "Message was successfully created!"
    context_object_name = 'message'
    success_url = reverse_lazy('sled_persistent_message:message-list')

    
@method_decorator(staff_member_required,name='dispatch')
class PersistentMessageUpdateView(BSModalUpdateView):
    model = PersistentMessage
    template_name = 'sled_persistent_message/message_update.html'
    form_class = PersistentMessageCreateUpdateForm
    success_message = 'Message was successfully updated!'
    context_object_name = 'message'
    success_url = reverse_lazy('sled_persistent_message:message-list')


@method_decorator(staff_member_required,name='dispatch')
class PersistentMessageDeleteView(BSModalDeleteView):
    model = PersistentMessage
    template_name = 'sled_persistent_message/message_delete.html'
    success_message = 'Message was deleted.'
    context_object_name = 'message'
    success_url = reverse_lazy('sled_persistent_message:message-list')
