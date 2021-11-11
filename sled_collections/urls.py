from django.urls import path, re_path
from django.views.generic.base import RedirectView
from sled_collections.views import CollectionDetailView, CollectionListView, CollectionCreateView

app_name = 'sled_collections'
urlpatterns = [
    path('', CollectionListView.as_view(), name='collections-list'),
    path('detail/',RedirectView.as_view(url='/sled_collections/',permanent=False),name='redirect-detail'),
    path('detail/<int:pk>/', CollectionDetailView.as_view(), name='collections-detail'),
    path('add/', CollectionCreateView.as_view(), name='collections-add'),
]
