from django.urls import path, re_path
from . import views

app_name = 'sled_lens_models'
urlpatterns = [
    path('lens-models-detail/<int:pk>', views.LensModelDetailView.as_view(), name='lens-model-detail'),
    path('lens-models-create/<int:lens>', views.LensModelCreateView.as_view(), name='lens-model-create'),
    path('lens-models-update/<int:pk>', views.LensModelUpdateView.as_view(), name='lens-model-update'),
    path('lens-models-delete/<int:pk>', views.LensModelDeleteView.as_view(), name='lens-model-delete'),
    path('lens-models-download/', views.LensModelDownloadView, name='lens-model-download'),
]
