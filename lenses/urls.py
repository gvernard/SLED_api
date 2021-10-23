from django.urls import path, re_path
from django.views.generic import TemplateView
from lenses.views import LensListView, LensDetailView, LensAddView, LensQueryView, LensUpdateView, LensDeleteView
#from . import views

app_name = 'lenses'
urlpatterns = [
    path('', TemplateView.as_view(template_name='lens_index.html'), name='lens-index'),
    path('query/',LensQueryView.as_view(),name='lens-query'),
    path('list/',LensListView.as_view(),name='lens-list'),
    path('add/',LensAddView.as_view(),name='lens-add'),
    path('update/',LensUpdateView.as_view(),name='lens-update'),
    path('delete/',LensDeleteView.as_view(),name='lens-delete'),
    #path('update/<int:lens>',LensUpdateView.as_view(),name='lens-update'),
    re_path('(?P<slug>[A-Za-z0-9\w|\W\- ]+)/$', LensDetailView.as_view(), name='lens-detail'),
]
