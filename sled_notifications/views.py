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
class NotificationListView(TemplateView):
    template_name = 'sled_notifications/notifications_list.html'
    
    def get_context_data(self, **kwargs):
        read = self.request.user.notifications.read().order_by('-timestamp')
        unread = self.request.user.notifications.unread().order_by('-timestamp')
        context = {'unread': list(unread), 'read': list(read)}
        print(context)
        self.request.user.notifications.unread().mark_all_as_read()
        return context



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
