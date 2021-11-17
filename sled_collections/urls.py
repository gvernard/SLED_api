from django.urls import path, re_path
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView

from . import views

app_name = 'sled_collections'
urlpatterns = [
    path('', views.CollectionListView.as_view(), name='collections-list'),
    path('detail/',RedirectView.as_view(url='/sled_collections/',permanent=False),name='redirect-detail'),
    path('detail/<int:pk>/', views.CollectionDetailView.as_view(), name='collections-detail'),
    path('add/', views.CollectionAddView.as_view(), name='collections-add'),
    path('delete/<int:pk>', views.CollectionDeleteView.as_view(), name='collection-delete'),
    path('update/<int:pk>', views.CollectionUpdateView.as_view(), name='collection-update'),
]
