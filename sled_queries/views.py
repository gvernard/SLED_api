from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib import messages
from django.urls import reverse,reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.sites.models import Site
from django.template.response import TemplateResponse

from bootstrap_modal_forms.generic import (
    BSModalCreateView,
    BSModalUpdateView,
    BSModalDeleteView,
    BSModalReadView,
)
from bootstrap_modal_forms.utils import is_ajax

from lenses.models import Users, SledQuery, Collection
from .forms import *


@method_decorator(login_required,name='dispatch')
class QueryListView(ListView):
    model = SledQuery
    allow_empty = True
    template_name = 'sled_queries/queries_list.html'

    def get_queryset(self):
        if self.kwargs.get('admin'):
            return SledQuery.accessible_objects.owned(Users.getAdmin().first())
        else:
            return SledQuery.accessible_objects.owned(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['queries'] = self.object_list
        return context

    def get(self, *args, **kwargs):
        if self.kwargs.get('admin') and not self.request.user.is_staff:
            return TemplateResponse(self.request,'simple_message.html',context={'message':'You are not authorized to view this page.'})
        return super(QueryListView,self).get(*args, **kwargs)

    
@method_decorator(login_required,name='dispatch')
class QuerySaveView(BSModalCreateView):
    model = SledQuery
    template_name = 'sled_queries/query_save.html'
    form_class = QuerySaveForm
    success_url = reverse_lazy('sled_queries:queries-list')

    def get_initial(self):
        cargo = self.request.GET
        #here we do a hacky copy of the initial cargo, which otherwise gets cleaned and any lists reduced to a single entry
        #convert the querydict to a python dict, note .dict does not do this properly in django
        self.initialcargo = dict(cargo)
        print('Within get_initial function:', self.initialcargo)
        return {'cargo': cargo}


    def form_valid(self, form):
        print(self.request)
        if not is_ajax(self.request.META):
            name = form.cleaned_data['name']
            description = form.cleaned_data['description']
            q = SledQuery(owner=self.request.user,name=name,description=description,access_level='PRI')

            #use the hacky copy of the initial cargo; people can save non-valid queries but they will
            #receive an error message when loading it in. This might be a dangerous way to do this since 
            #people can store strings in the database, but they do have to be validated for this function to run...
            cargo = q.compress_to_cargo(self.initialcargo)
            if 'page' in cargo.keys():
                cargo.pop('page')

            q.cargo = cargo
            q.save()
            messages.add_message(self.request,messages.SUCCESS,"Query <b>"+name+"</b> was successfully saved!")
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

    def get_queryset(self):
        if self.kwargs.get('admin'):
            return SledQuery.accessible_objects.owned(Users.getAdmin().first())
        else:
            return SledQuery.accessible_objects.owned(self.request.user)      

    def get_success_url(self):
        if self.kwargs.get('admin'):
            return reverse_lazy('sled_queries:queries-list-admin')
        else:
            return reverse_lazy('sled_queries:queries-list')




@method_decorator(login_required,name='dispatch')
class QueryDeleteView(BSModalDeleteView):
    model = SledQuery
    template_name = 'sled_queries/query_delete.html'
    success_message = 'Success: Query was deleted.'
    context_object_name = 'query'

    def get_queryset(self):
        if self.kwargs.get('admin'):
            return SledQuery.accessible_objects.owned(Users.getAdmin().first())
        else:
            return SledQuery.accessible_objects.owned(self.request.user)

    def get_success_url(self):
        if self.kwargs.get('admin'):
            return reverse_lazy('sled_queries:queries-list-admin')
        else:
            return reverse_lazy('sled_queries:queries-list')


    
@method_decorator(login_required,name='dispatch')
class QueryLinkView(BSModalReadView):
    model = SledQuery
    template_name = 'sled_queries/query_link.html'
    context_object_name = 'query'

    def get_queryset(self):
        return SledQuery.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site = Site.objects.get_current()
        context["link"] = self.request.scheme + '://' + site.domain + self.object.get_GET_url()
        return context



        
# View for dynamic lens queries and collections
@method_decorator(login_required,name='dispatch')
class StandardQueriesView(ListView):
    model = SledQuery
    allow_empty = True
    template_name = 'lenses/lens_all_collections.html'

    def get_queryset(self):
        admin = Users.objects.get(username='admin')
        admin_queries = SledQuery.accessible_objects.owned(admin)
        return admin_queries

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        admin = Users.objects.get(username='admin')
        admin_queries = SledQuery.accessible_objects.owned(admin)
        context['queries'] = admin_queries

        collections = Collection.accessible_objects.owned(admin)
        context['collections'] = collections
        return context


