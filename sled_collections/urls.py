from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_collections'
urlpatterns = [
    path('', views.CollectionSplitListView.as_view(), name='collections-list'),
    path('detail/', RedirectView.as_view(url='/sled_collections/',permanent=False), name='redirect-detail'),
    path('make-collection/<str:obj_type>',views.CollectionCreateView.as_view(),name='collection-create'),
    path('add-items/<str:obj_type>', views.CollectionAddItemsView.as_view(), name='collection-add-items'),
    path('remove-items/<int:pk>', views.CollectionRemoveItemsView.as_view(), name='collection-remove-items'),
    path('detail/<int:pk>', views.CollectionDetailView.as_view(), name='collections-detail'),
    path('delete/<int:pk>', views.CollectionDeleteView.as_view(), name='collection-delete'),
    path('update/<int:pk>', views.CollectionUpdateView.as_view(), name='collection-update'),
    path('make-public/<int:pk>', views.CollectionMakePublicView.as_view(), name='collection-make-public'),
    path('give-access/<int:pk>', views.CollectionGiveRevokeAccessView.as_view(), kwargs={'mode':'give'}, name='collection-give-access'),
    path('revoke-access/<int:pk>', views.CollectionGiveRevokeAccessView.as_view(), kwargs={'mode':'revoke'}, name='collection-revoke-access'),
    path('ask-access/<int:pk>', views.CollectionAskAccessView.as_view(), name='collection-ask-access'),
    path('cede-ownership/<int:pk>', views.CollectionCedeOwnershipView.as_view(), name='collection-cede-ownership'),
    path('view-access/<int:pk>', views.CollectionViewAccessView.as_view(), name='collection-view-access'),
    path('export-csv/<int:pk>', views.CollectionExportToCSVView.as_view(), name='export-csv'),    
]
