from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_collections'
urlpatterns = [
    path('', views.CollectionListView.as_view(), name='collections-list'),
    path('list/', views.CollectionListView2.as_view(), name='collections-list2'), # This is used to add items via a lens query
    path('detail/',RedirectView.as_view(url='/sled_collections/',permanent=False),name='redirect-detail'),
    path('detail/<int:pk>', views.CollectionDetailView.as_view(), name='collections-detail'),
    path('add/', views.CollectionAddView.as_view(), name='collections-add'),
    path('delete/<int:pk>', views.CollectionDeleteView.as_view(), name='collection-delete'),
    path('update/<int:pk>', views.CollectionUpdateView.as_view(), name='collection-update'),
    path('add-items/<int:pk>', views.CollectionAddItemsView.as_view(), name='collection-add-items'),
]
