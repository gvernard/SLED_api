from django.urls import path
from django.views.generic.base import RedirectView

from . import views

app_name = 'sled_notifications'
urlpatterns = [
    path('',views.NotificationListView.as_view(),name='notifications-list'),
    path('notifications-list-admin', views.NotificationListView.as_view(),kwargs={'admin':True},name='notifications-list-admin'),
    path('detail/',RedirectView.as_view(url='/sled_notifications/',permanent=False),name='redirect-detail'),
    path('detail/<int:pk>',views.NotificationDetailView.as_view(),name='notifications-detail'),
]
