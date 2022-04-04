from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib import messages
from django.urls import reverse,reverse_lazy
from django.http import HttpResponseRedirect

from bootstrap_modal_forms.generic import (
    BSModalCreateView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.utils import is_ajax

from lenses.models import Users, SledQuery
from .forms import *


@method_decorator(login_required,name='dispatch')
class QueryListView(ListView):
    model = SledQuery
    allow_empty = True
    template_name = 'sled_queries/queries_list.html'

    def get_queryset(self):
        return SledQuery.accessible_objects.owned(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['queries'] = self.object_list
        return context


@method_decorator(login_required,name='dispatch')
class QuerySaveView(BSModalCreateView):
    model = SledQuery
    template_name = 'sled_queries/query_save.html'
    form_class = QuerySaveForm
    success_url = reverse_lazy('sled_queries:queries-list')

    def get_initial(self):
        cargo = self.request.GET
        return {'cargo': cargo}

    def form_valid(self,form):
        if not is_ajax(self.request.META):
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            q = SledQuery(owner=self.request.user,name=name,description=description,access_level='PRI')
            cargo = q.compress_to_cargo(form.cleaned_data['cargo'])
            if 'page' in cargo.keys():
                cargo.pop('page')
            q.cargo = cargo
            q.save()
            messages.add_message(self.request,messages.SUCCESS,'Query <b>"'+name+'"</b> was successfully saved!')
            return HttpResponseRedirect(reverse_lazy('sled_queries:queries-list')) 
            #return HttpResponseRedirect(reverse('sled_collections:collections-detail',kwargs={'pk':mycollection.id})) 
        else:
            response = super().form_valid(form)
            return response


@method_decorator(login_required,name='dispatch')
class QueryUpdateView(BSModalUpdateView):
    model = SledQuery
    template_name = 'sled_queries/query_save.html'
    form_class = QuerySaveForm
    success_message = 'Success: Query was updated.'
    success_url = reverse_lazy('sled_queries:queries-list')

    def get_queryset(self):
        return SledQuery.accessible_objects.owned(self.request.user)


@method_decorator(login_required,name='dispatch')
class QueryDeleteView(BSModalDeleteView):
    model = SledQuery
    template_name = 'sled_queries/query_delete.html'
    success_message = 'Success: Query was deleted.'
    success_url = reverse_lazy('sled_queries:queries-list')
    context_object_name = 'query'

    def get_queryset(self):
        return SledQuery.accessible_objects.owned(self.request.user)


@method_decorator(login_required,name='dispatch')
class QueryLinkView(BSModalReadView):
    model = SledQuery
    template_name = 'sled_queries/query_link.html'
    context_object_name = 'query'

    def get_queryset(self):
        return SledQuery.accessible_objects.owned(self.request.user)
