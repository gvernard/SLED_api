from django.http import HttpResponse
from django.views.generic import TemplateView


class HowToView(TemplateView):
    template_name = "sled_howto/howto.html"

    def get_context_data(self, **kwargs):
        context = super(HowToView,self).get_context_data(**kwargs)
        return context
