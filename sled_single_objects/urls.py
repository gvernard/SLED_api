from django.urls import path, re_path
from django.views.generic import TemplateView
from . import views

app_name = 'so'
urlpatterns = [
    path('cede-ownership/',views.SingleObjectCedeOwnershipView.as_view(),name='so-cede-ownership'),
    path('make-private/',views.SingleObjectMakePrivateView.as_view(),name='so-make-private'),
    path('give-access/',views.SingleObjectGiveRevokeAccessView.as_view(),kwargs={'mode':'give'},name='so-give-access'),
    path('revoke-access/',views.SingleObjectGiveRevokeAccessView.as_view(),kwargs={'mode':'revoke'},name='so-revoke-access'),
    path('make-public/',views.SingleObjectMakePublicView.as_view(),name='so-make-public'),
]
