from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView
from actstream.models import target_stream
from lenses.models import Users

class HomePageView(TemplateView):
    template_name = 'home/home_index.html'

    def get_context_data(self, **kwargs):
        stream = target_stream(Users.objects.get(username='admin'))
        context = {'stream': stream}
        return context
