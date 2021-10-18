from django.urls import path, re_path
from django.views.generic import TemplateView
from lenses.views import LensListView, LensDetailView, LensCreateView, LensQueryView
#from . import views

app_name = 'lenses'
urlpatterns = [
    path('', TemplateView.as_view(template_name="lens_index.html"), name='lens-index'),
    path('query/',LensQueryView.as_view(),name='lens-query'),
    path('list/',LensListView.as_view(),name='lens-list'),
    path('add/',LensCreateView.as_view(),name='lens-add'),
    #path('check/',LensCreateView.as_view(),name='lens-check'),
    re_path('(?P<slug>[A-Za-z0-9\w|\W\- ]+)/$', LensDetailView.as_view(), name='lens-detail'),
]
