from django.urls import path, re_path
from django.views.generic import TemplateView
from . import views


app_name = 'lenses'
urlpatterns = [
    path('',TemplateView.as_view(template_name='lenses/lens_index.html'), name='lens-index'),
    path('query/',views.LensQueryView.as_view(),name='lens-query'),
    path('all-collections/',views.StandardQueriesView.as_view(),name='lens-all-collections'),
    path('add/',views.LensAddView.as_view(),name='lens-add'),
    path('update/',views.LensUpdateView.as_view(),name='lens-update'),
    path('update-modal/<int:pk>',views.LensUpdateModalView.as_view(),name='lens-update-modal'),
    path('collage/',views.LensCollageView.as_view(),name='lens-collage'),
    path('export/',views.ExportToCsv.as_view(),name='export-csv'),
    path('delete/',views.LensDeleteView.as_view(),name='lens-delete'),
    path('make-public/',views.LensMakePublicView.as_view(),name='lens-make-public'),
    path('resolve-duplicates/<int:pk>',views.LensResolveDuplicatesView.as_view(),name='resolve-duplicates'),
    path('add-data/<int:pk>',views.LensAddDataView.as_view(),name='add-data'),
    path('detail/<int:pk>',views.LensDetailView.as_view(),name='lens-detail'),
]
