from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator

from lenses.models import Users, SledGroups, Lenses


from .forms import LensFormSet
from django.urls import reverse_lazy,reverse
from django.shortcuts import redirect


# View for lens queries
@method_decorator(login_required,name='dispatch')
class LensQueryView(ListView):
    model = Lenses
    template_name = 'lens_list.html'
    context_object_name = 'lenses'

    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user).order_by('ra')

# View for any list of lenses
@method_decorator(login_required,name='dispatch')
class LensListView(ListView):
    model = Lenses
    template_name = 'lens_list.html'
    context_object_name = 'lenses'

    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user).order_by('ra')

# View for a single lens
@method_decorator(login_required,name='dispatch')
class LensDetailView(DetailView):
    model = Lenses
    template_name = 'lens_detail.html'
    context_object_name = 'lens'
    slug_field = 'name'
    
    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user)

# View to add new lenses
@method_decorator(login_required,name='dispatch')
class LensCreateView(TemplateView):
    model = Lenses
    template_name = 'lens_add.html'
    fields = ['ra','dec']
    
    def get(self, *args, **kwargs):
        formset = LensFormSet(queryset=Lenses.accessible_objects.none())
        return self.render_to_response({'lens_formset': formset})

    # Define method to handle POST request
    def post(self, *args, **kwargs):
        formset = LensFormSet(data=self.request.POST)

        print('total/filled: ',formset.total_form_count(),formset.initial_form_count())
        
        # Check if submitted forms are valid
        if formset.has_changed() and formset.is_valid():
            print('VALID')
            print(formset.cleaned_data)
            instances = formset.save(commit=False)
            for i,lens in enumerate(instances):
                neis = lens.get_DB_neighbours(16)
                if len(neis) == 0:
                    lens.owner = self.request.user
                    print('(%d) %s (%f,%f) - INSERT' % (i,lens.name,lens.ra,lens.dec))
                    #lens.save()
                else:
                    print('(%d) %s (%f,%f) - Proximity alert (%d)' % (i,lens.name,lens.ra,lens.dec,len(neis)))
            return self.render_to_response({'lens_formset': formset})
        else:
            print('NOT VALID')
            print(formset.errors)
            print(formset.non_form_errors())
            #return redirect('/lenses/query/')
            return self.render_to_response({'lens_formset': formset})
