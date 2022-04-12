from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views

app_name = 'sled_instrument'
urlpatterns = [
    path('', views.InstrumentListView.as_view(), name='instrument-list'),
    path('add/', views.InstrumentCreateView.as_view(), name='instrument-add'),
    path('delete/<int:pk>', views.InstrumentDeleteView.as_view(), name='instrument-delete'),
    path('update/<int:pk>', views.InstrumentUpdateView.as_view(), name='instrument-update')
]
