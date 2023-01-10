from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import TemplateView
from actstream.models import target_stream
from django.core.paginator import Paginator
from lenses.models import Users

class HomePageView(TemplateView):
    template_name = 'home/home_index.html'

    def get_context_data(self, **kwargs):
        stream = target_stream(Users.objects.get(username='admin'))
        context = {'stream': stream}
        return context

class HomeAllActivityView(TemplateView):
    template_name = 'home/home_all_activity.html'

    def get_context_data(self, **kwargs):
        stream = target_stream(Users.objects.get(username='admin'))

        # Paginator for stream
        stream_paginator = Paginator(stream,50)
        stream_page_number = self.request.GET.get('stream-page',1)
        context = {'N_stream_total': stream_paginator.count,
                   'stream_range': stream_paginator.page_range,
                   'stream': stream_paginator.get_page(stream_page_number)
                   }
        return context
