from django.urls import path, re_path
from django.views.generic.base import RedirectView

from . import views

app_name = 'sled_tasks'
urlpatterns = [
    path('', views.TaskListView.as_view(),name='tasks-list'),
    path('task-list-admin', views.TaskListView.as_view(),kwargs={'admin':True},name='tasks-list-admin'),
    path('detail/',RedirectView.as_view(url='/sled_tasks/',permanent=False),name='redirect-detail'),
    path('detail-owner/<int:pk>', views.TaskDetailOwnerView.as_view(),name='tasks-detail-owner'),
    path('detail-admin-owner/<int:pk>', views.TaskDetailOwnerView.as_view(),kwargs={'admin':True},name='tasks-detail-admin-owner'),
    path('detail-recipient/<int:pk>', views.TaskDetailRecipientView.as_view(),name='tasks-detail-recipient'),
    path('detail-admin-recipient/<int:pk>', views.TaskDetailRecipientView.as_view(),kwargs={'admin':True},name='tasks-detail-admin-recipient'),
    path('detail-inspect/<int:pk>', views.TaskInspectDetailView.as_view(),name='tasks-detail-inspect'),
    path('detail-inspect-owner/<int:pk>', views.TaskInspectDetailOwnerView.as_view(),name='tasks-detail-inspect-owner'),
    path('detail-request-update-owner/<int:pk>', views.TaskRequestUpdateDetailOwnerView.as_view(),name='tasks-detail-request-update-owner'),
    path('detail-request-update-recipient/<int:pk>', views.TaskRequestUpdateDetailRecipientView.as_view(),name='tasks-detail-request-update-recipient'),
    path('detail-merge/<int:pk>', views.TaskMergeDetailView.as_view(),name='tasks-detail-merge'),
    path('detail-merge-owner/<int:pk>', views.TaskMergeDetailOwnerView.as_view(),name='tasks-detail-merge-owner'),
    path('detail-duplicates-complete/<int:pk>', views.TaskResolveDuplicatesCompleteDetailView.as_view(),name='tasks-detail-resolve-duplicates-complete'),
    path('delete-task/<int:pk>', views.TaskDeleteView.as_view(),name='tasks-delete'),
]
