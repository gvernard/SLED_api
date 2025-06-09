from django.urls import path, re_path
from . import views

app_name = 'sled_lens_models'
urlpatterns = [
    path('lens-model-detail/<int:pk>',views.LensModelDetailView.as_view(),name='lens-model-detail-view'),
    path('test/<int:lens>', views.test.as_view(), name='test'),
    path('lens-models/<int:pk>/create/', LensModelCreateView.as_view(), name='lens-model-create'),

]

 #must be consistant in models urls.py file (name must be called on in models) 