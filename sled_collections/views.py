from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, DetailView, ListView
from django.utils.decorators import method_decorator

from lenses.models import Collection

@method_decorator(login_required,name='dispatch')
class CollectionListView(ListView):
    model = Collection
    allow_empty = True
    template_name = 'collection_list.html'
    paginate_by = 100  # if pagination is desired
    
    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collections'] = self.object_list
        return context

    

@method_decorator(login_required,name='dispatch')
class CollectionDetailView(DetailView):
    model = Collection
    template_name = 'collection_detail.html'

    def get_queryset(self):
        return self.model.accessible_objects.owned(self.request.user)
    
    def get_context_data(self, **kwargs):
        if self.object.owner == self.request.user:
            context = super().get_context_data(**kwargs)
            context['collection'] = self.object
            return context
        else:
            message = "You are not the owner of this collection!"
            return TemplateResponse(request,'simple_message.html',context={'message':message})
