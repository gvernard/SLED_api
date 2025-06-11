from django.urls import path, re_path
from . import views

app_name = 'sled_lens_models'
urlpatterns = [
    path('lens-model-detail/<int:pk>',views.LensModelDetailView.as_view(),name='lens-model-detail-view'),
    path('test/<int:lens>', views.test.as_view(), name='test'),
    path('lens-models-create/<int:lens>', views.LensModelCreateView.as_view(), name='lens-model-create'),
    #path('lens-models-update/<int:pk>', views.CollectionRemoveItemsView.as_view(), name='collection-remove-items'),

]

 #must be consistant in models urls.py file (name must be called on in models) 
 #name is used as internal reference by jango server - for reverse a view (going from view to url)
 #sled_lens_models:name creates a url