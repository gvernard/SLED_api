from django.urls import path, re_path
from django.views.generic import TemplateView
from . import views


app_name = 'lenses'
urlpatterns = [
    path('',TemplateView.as_view(template_name='lenses/lens_index.html'), name='lens-index'),
    path('export/',views.ExportToCSV.as_view(),name='export-csv'),
    path('query/',views.LensQueryView.as_view(),name='lens-query'),
    path('add/',views.LensAddView.as_view(),name='lens-add'),
    path('update/',views.LensUpdateView.as_view(),name='lens-update'),
    path('update-modal/<int:pk>',views.LensUpdateModalView.as_view(),name='lens-update-modal'),
    path('collage/',views.LensCollageView.as_view(),name='lens-collage'),
    path('delete/',views.LensDeleteView.as_view(),name='lens-delete'),
    path('make-public/',views.LensMakePublicView.as_view(),name='lens-make-public'),
    path('resolve-duplicates/<int:pk>',views.LensResolveDuplicatesView.as_view(),name='resolve-duplicates'),
    path('add-data/<int:pk>',views.LensAddDataView.as_view(),name='add-data'),
    path('detail/<int:pk>',views.LensDetailView.as_view(),name='lens-detail'),
    path('ajax/follow-unfollow',views.follow_unfollow,name="follow-unfollow"),
    path('ask-access/<int:pk>', views.LensAskAccessView.as_view(),name='lens-ask-access'),
    path('connections/<int:pk>', views.LensConnectionsSummaryView.as_view(),name='lens-connections'),
    path('request-update/<int:pk>', views.LensRequestUpdateView.as_view(),name='lens-request-update'),
]
