from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_collections'
urlpatterns = [
    #path('', views.CollectionListView.as_view(), name='collections-list'),
    path('', views.CollectionSplitListView.as_view(), name='collections-list'),
    path('list/', views.CollectionListView2.as_view(), name='collections-list2'), # This is used to add items via a lens query
    path('add/', views.CollectionAddView.as_view(), name='collections-add'),
    path('detail/',RedirectView.as_view(url='/sled_collections/',permanent=False),name='redirect-detail'),
    path('detail/<int:pk>', views.CollectionDetailView.as_view(), name='collections-detail'),
    path('delete/<int:pk>', views.CollectionDeleteView.as_view(), name='collection-delete'),
    path('update/<int:pk>', views.CollectionUpdateView.as_view(), name='collection-update'),
    path('add-items/<int:pk>', views.CollectionAddItemsView.as_view(), name='collection-add-items'),
    path('give-access/<int:pk>',views.CollectionGiveRevokeAccessView.as_view(),kwargs={'mode':'give'},name='collection-give-access'),
    path('revoke-access/<int:pk>',views.CollectionGiveRevokeAccessView.as_view(),kwargs={'mode':'revoke'},name='collection-revoke-access'),
    path('ask-access/<int:pk>',views.CollectionAskAccessView.as_view(),name='collection-ask-access'),
]
