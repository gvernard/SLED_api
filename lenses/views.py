from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from django.views.generic import ListView, DetailView, TemplateView
from django.utils.decorators import method_decorator

from lenses.models import Users, SledGroups, Lenses


from .forms import LensFormSet
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

# View for a single lens
@method_decorator(login_required,name='dispatch')
class LensDetailView(DetailView):
    model = Lenses
    template_name = 'lens_detail.html'
    context_object_name = 'lens'
    slug_field = 'name'
    
    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user)


    
    
# View for any list of lenses
@method_decorator(login_required,name='dispatch')
class LensListView(ListView):
    model = Lenses
    template_name = 'lens_list.html'
    context_object_name = 'lenses'

    def get_queryset(self):
        return Lenses.accessible_objects.all(self.request.user).order_by('ra')

    def get_context_data(self):
        '''
        Adds the model to the context data.
        '''
        context          = super(ListView, self).get_context_data()
        context['model'] = self.model
        context['fields_to_display'] = ['name','ra','dec','z_lens','z_source','access_level']
        return context

    def post(self,request,*args,**kwargs):
        selected = request.POST.getlist('myselect')
        if selected:
            lenses = Lenses.accessible_objects.all(self.request.user).filter(id__in=selected).order_by('ra')
        else:
            lenses = self.get_queryset()
        return render(request, self.template_name,{'lenses': lenses})
                


    
# View to add new lenses
@method_decorator(login_required,name='dispatch')
class LensCreateView(TemplateView):
    model = Lenses
    template_name = 'lens_add.html'
    
    def get_my_context(self,myformset,**kwargs):
        for f in myformset.forms:
            f.initial['insert'] = ''
        mode = kwargs.get('mode','create')
        existing = kwargs.get('existing',[None]*len(myformset))
        context = {'lens_formset': myformset,
                   'new_existing': zip(myformset,existing),
                   'mode': mode
                   }
        return context

    def get_proximity(self,instances,cleaned_data):
        existing_prox = [None]*len(instances)
        flag = False
        for i,lens in enumerate(instances):
            neis = lens.get_DB_neighbours(16)
            if len(neis) != 0 and cleaned_data[i]['insert'] == '':
                flag = True
                existing_prox[i] = neis
                print('(%d) %s (%f,%f) - Proximity alert (%d)' % (i,lens.name,lens.ra,lens.dec,len(neis)))
        return flag,existing_prox

    
    
    def get(self, *args, **kwargs):
        myformset = LensFormSet(queryset=Lenses.accessible_objects.none())
        return self.render_to_response(self.get_my_context(myformset))

    

    def post(self, request, *args, **kwargs):
        mode = request.POST.get('mode','create')
        check = request.POST.get('check')
        print(mode,check)


        if mode == 'create':
            # Create new objects
            
            if check:
                # Submitting to itself, perform all the checks
                myformset = LensFormSet(data=self.request.POST)
                if myformset.has_changed() and myformset.is_valid():
                    instances = myformset.save(commit=False)
                    flag,existing_prox = self.get_proximity(instances,myformset.cleaned_data)
                
                    if flag:
                        # Display duplicates
                        return self.render_to_response(self.get_my_context(myformset,existing=existing_prox,mode=mode))
                    else:
                        to_insert = []
                        for i,lens in enumerate(instances):
                            if myformset.cleaned_data[i]['insert'] != 'no':
                                lens.owner = self.request.user
                                lens.create_name()
                                to_insert.append(lens)
                        if to_insert:
                            Lenses.objects.bulk_create(to_insert)
                            return HttpResponse('Lenses successfully added to the database')
                        else:
                            return HttpResponse('No new lenses to insert.')
                else:
                    return self.render_to_response(self.get_my_context(myformset,mode=mode))

            else:
                self.get(*args,**kwargs)
           
            
        else:
            # Update existing objects

            if check:
                # Submitting to itself, perform all the checks
                myformset = LensFormSet(self.request.POST)
                if myformset.has_changed() and myformset.is_valid():
                    instances = myformset.save(commit=False)
                    for i,myform in enumerate(myformset.forms):
                        to_check = []
                        if 'ra' in myform.changed_data or 'dec' in myform.changed_data:
                            to_check.append(instances[i])

                    # Double 'if' here. First check, then if there is proximity render. If not, proceed with the update.
                    if to_check:
                        flag,existing_prox = self.get_proximity(to_check,myformset.cleaned_data)
                        if flag:
                            return self.render_to_response(self.get_my_context(myformset,existing=existing_prox,mode=mode))

                    to_update = []
                    for i,myform in enumerate(myformset.forms):
                        if myform.has_changed() and myform.cleaned_data['insert'] != 'no':
                            to_update.append(instances[i])
                    if to_update:
                        for lens in to_update:
                            lens.save()
                        return HttpResponse('Lenses successfully updated')
                    else:
                        return HttpResponse('No lenses to update.')
                else:
                    return self.render_to_response(self.get_my_context(myformset,mode=mode))
                
            else:
                ids = request.POST.getlist('ids')
                if ids:
                    lenses = Lenses.objects.filter(owner=self.request.user).filter(id__in=ids).order_by('ra')
                    initial_data = list(lenses.values())
                    myformset = LensFormSet(queryset=lenses,initial=initial_data)
                    return self.render_to_response(self.get_my_context(myformset,mode=mode))
                else:
                    return HttpResponse('You must select which lenses to update from your User profile page: <link>')




