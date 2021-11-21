from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, DetailView, ListView

from bootstrap_modal_forms.generic import BSModalReadView

import notifications
from lenses.models import Users
from swapper import load_model

Notification = load_model('notifications', 'Notification')


@method_decorator(login_required,name='dispatch')
class NotificationListView(ListView):
    model = Notification
    template_name = 'sled_notifications/notifications_list.html'
    context_object_name = 'notes'
    
    def get_queryset(self):
        return self.request.user.notifications.all().order_by('-unread','-timestamp')


@method_decorator(login_required,name='dispatch')
class NotificationDetailView(BSModalReadView):
    model = Notification
    template_name = 'sled_notifications/notifications_detail.html'
    context_object_name = 'note'

    def get_queryset(self):
        return self.request.user.notifications.all()

    def get_object(self):
        obj = super().get_object()
        obj.mark_as_read()
        return obj
