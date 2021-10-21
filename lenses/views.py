from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator

from lenses.models import Users, SledGroups, Lenses


from .forms import LensFormSet, ActionForm
from django.forms import formset_factory
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

# View to check lenses
class LensCheckView(TemplateView):
    """
    A view that renders a template.  This view will also pass into the context
    any keyword arguments passed by the url conf.
    """
    template_name = 'lens_check.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        to_create = context['to_create']
        duplicate = context['duplicate']
        existing = context['existing']
        actions = ActionFormSet(extra=len(duplicate))
        zipped = zip(duplicate,existing,actions)
        context = {'to_create': to_create,
                   'zipped': zipped}
        return self.render_to_response(context)
    
# View to add new lenses
@method_decorator(login_required,name='dispatch')
class LensCreateView(TemplateView):
    model = Lenses
    template_name = 'lens_add.html'
    
    def get(self, *args, **kwargs):
        myformset = LensFormSet()
        #myforms = myformset()
        existing = [None]*len(myformset)
        new_existing = zip(myformset,existing)
        return self.render_to_response({'lens_formset': myformset,'new_existing':new_existing})

    # Define method to handle POST request
    def post(self, request, *args, **kwargs):
        myformset = LensFormSet(data=self.request.POST)
        
        # Check if submitted forms are valid
        if myformset.has_changed() and myformset.is_valid():
            instances = myformset.save(commit=False)
            existing_prox = [None]*len(instances)
            flag = False
            for i,lens in enumerate(instances):
                neis = lens.get_DB_neighbours(16)
                if len(neis) != 0:
                    flag = True
                    existing_prox[i] = neis
                    print('(%d) %s (%f,%f) - Proximity alert (%d)' % (i,lens.name,lens.ra,lens.dec,len(neis)))

            if flag:
                new_existing = zip(myformset,existing_prox)
                return self.render_to_response({'lens_formset':myformset,'new_existing':new_existing})
            else:
                for lens in instances:
                    lens.owner = self.request.user
                    lens.create_name()
                Lenses.objects.bulk_create(instances)
                return HttpResponse('Lenses successfully added to the database')

        else:
            existing = [None]*len(myformset)
            new_existing = zip(myformset,existing)
            return self.render_to_response({'lens_formset': myformset,'new_existing':new_existing})
