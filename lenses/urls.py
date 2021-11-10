from django.urls import path, re_path
from django.views.generic import TemplateView
from lenses.views import LensDetailView, LensAddView, LensQueryView, LensCollageView, LensUpdateView, LensDeleteView, LensGiveRevokeAccessView, LensMakePrivateView, LensMakePublicView, LensCedeOwnershipView, LensMergeResolutionView, LensMakeCollectionView
#from . import views

app_name = 'lenses'
urlpatterns = [
    path('',TemplateView.as_view(template_name='lens_index.html'), name='lens-index'),
    path('query/',LensQueryView,name='lens-query'),
    path('all-collections/',TemplateView.as_view(template_name='lens_all_collections.html'),name='lens-all-collections'),
    path('add/',LensAddView.as_view(),name='lens-add'),
    path('update/',LensUpdateView.as_view(),name='lens-update'),
    path('collage/',LensCollageView,name='lens-collage'),
    path('delete/',LensDeleteView.as_view(),name='lens-delete'),
    path('give-access/',LensGiveRevokeAccessView.as_view(),kwargs={'mode':'give'},name='lens-give-access'),
    path('revoke-access/',LensGiveRevokeAccessView.as_view(),kwargs={'mode':'revoke'},name='lens-revoke-access'),
    path('cede-ownership/',LensCedeOwnershipView.as_view(),name='lens-cede-ownership'),
    path('make-private/',LensMakePrivateView.as_view(),name='lens-make-private'),
    path('make-public/',LensMakePublicView.as_view(),name='lens-make-public'),
    path('merge-resolution/',LensMergeResolutionView.as_view(),name='lens-merge-resolution'),
    path('make-collection/',LensMakeCollectionView.as_view(),name='lens-make-collection'),
    re_path('(?P<slug>[A-Za-z0-9\w|\W\- ]+)/$', LensDetailView.as_view(), name='lens-detail'),
]
