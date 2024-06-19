from django.shortcuts import render
from django.views.generic import TemplateView


class GuideView(TemplateView):
    template_name = "sled_guide/guide.html"
