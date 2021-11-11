from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.utils.decorators import method_decorator
from django.apps import apps

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


@method_decorator(login_required,name='dispatch')
class CollectionCreateView(CreateView):
    model = Collection
    fields = ["name","description","myitems"]
    template_name = "collection_create_form.html"

    def form_valid(self,form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)

        items = []
        if self.request.method=='POST':
            obj_type = self.request.POST.get('obj_type')
            ids = [ pk for pk in self.request.POST.getlist('ids') if pk.isdigit() ]
            if ids:
                items = apps.get_model(app_label='lenses',model_name=obj_type).accessible_objects.in_ids(self.request.user,ids)

        context['items'] = items
        return context
