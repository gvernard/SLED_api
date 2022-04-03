from django.urls import path, re_path
from django.views.generic import TemplateView
from . import views


app_name = 'lenses'
urlpatterns = [
    path('',TemplateView.as_view(template_name='lenses/lens_index.html'), name='lens-index'),
    path('query/',views.LensQueryView.as_view(),name='lens-query'),
    path('all-collections/',TemplateView.as_view(template_name='lenses/lens_all_collections.html'),name='lens-all-collections'),
    path('add/',views.LensAddView.as_view(),name='lens-add'),
    path('update/',views.LensUpdateView.as_view(),name='lens-update'),
    path('collage/',views.LensCollageView.as_view(),name='lens-collage'),
    path('delete/',views.LensDeleteView.as_view(),name='lens-delete'),
    path('give-access/',views.LensGiveRevokeAccessView.as_view(),kwargs={'mode':'give'},name='lens-give-access'),
    path('revoke-access/',views.LensGiveRevokeAccessView.as_view(),kwargs={'mode':'revoke'},name='lens-revoke-access'),
    path('cede-ownership/',views.LensCedeOwnershipView.as_view(),name='lens-cede-ownership'),
    path('make-private/',views.LensMakePrivateView.as_view(),name='lens-make-private'),
    path('make-public/',views.LensMakePublicView.as_view(),name='lens-make-public'),
    path('resolve-duplicates/<int:pk>',views.LensResolveDuplicatesView.as_view(),name='resolve-duplicates'),
    path('add-data/<int:pk>',views.LensAddDataView.as_view(),name='add-data'),
    path('detail/<int:pk>',views.LensDetailView.as_view(),name='lens-detail'),
]
