from django.urls import path, re_path
from django.views.generic.base import RedirectView

from . import views

app_name = 'sled_tasks'
urlpatterns = [
    path('', views.TaskListView.as_view(),name='tasks-list'),
    path('detail/',RedirectView.as_view(url='/sled_tasks/',permanent=False),name='redirect-detail'),
    path('detail-owner/<int:pk>', views.TaskDetailOwnerView.as_view(),name='tasks-detail-owner'),
    path('detail-recipient/<int:pk>', views.TaskDetailRecipientView.as_view(),name='tasks-detail-recipient'),
]
