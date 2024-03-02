from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_admin_collections'
urlpatterns = [
    path('detail/<int:pk>', views.AdminCollectionDetailView.as_view(), name='admin-collections-detail'),
]
