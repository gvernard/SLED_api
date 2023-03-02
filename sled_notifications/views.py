from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, DetailView, ListView
from django.core.paginator import Paginator

from bootstrap_modal_forms.generic import BSModalReadView

import notifications
from lenses.models import Users
from swapper import load_model

Notification = load_model('notifications', 'Notification')


@method_decorator(login_required,name='dispatch')
class NotificationListView(TemplateView):
    template_name = 'sled_notifications/notifications_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.kwargs.get('admin'):
            admin = Users.getAdmin().first()
            read = admin.notifications.read().order_by('-timestamp')
            unread = admin.notifications.unread().order_by('-timestamp')
            admin.notifications.unread().mark_all_as_read()
        else:
            read = self.request.user.notifications.read().order_by('-timestamp')
            unread = self.request.user.notifications.unread().order_by('-timestamp')
            self.request.user.notifications.unread().mark_all_as_read()

        n_paginator = Paginator(read,50)
        n_page_number = self.request.GET.get('notifications_read-page',1)
        if 'admin' in self.kwargs.keys():
            admin_page = True
        else:
            admin_page = False
            
        context = {'unread': list(unread),
                   'N_read': n_paginator.count,
                   'read_range': n_paginator.page_range,
                   'read': n_paginator.get_page(n_page_number),
                   'admin_page': admin_page
                   }
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
