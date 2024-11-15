# Standard library imports
import csv

# Django imports
from django.shortcuts import render  
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, DetailView, ListView
from django.db.models import F, Q, Min, Max
from django.urls import reverse_lazy, reverse  
from django.http import HttpResponse
from django.core.paginator import Paginator
from rest_framework.renderers import JSONRenderer

# Third party app imports 
from bootstrap_modal_forms.mixins import is_ajax
from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView

# Local app imports
from .forms import *  
from lenses.forms import DownloadChooseForm
from lenses.models import Lenses, Paper
from api.download_serializers import LensDownSerializerAll, LensDownSerializer



@method_decorator(login_required,name='dispatch')
class PaperQueryView(TemplateView):
    model = Paper
    template_name = 'sled_papers/paper_query.html'

    def paper_query(self,cleaned_data):
        search_term = cleaned_data['search_term']
        year_min = cleaned_data['year_min']
        year_max = cleaned_data['year_max']
        print(cleaned_data)
        #I've changed this because it was not what I thought it would do
        #and I want to keep it consistent with how the lens query max min fields work
        if year_min and year_max:
            papers = Paper.objects.filter(year__range=[year_min,year_max])
        elif year_min and not year_max:
            papers = Paper.objects.filter(year__gte=year_min)
        elif year_max and not year_min:
            papers = Paper.objects.filter(year__lte=year_max)
        else:
            papers = Paper.objects.all()
        if search_term!='':
            papers = papers.filter(Q(first_author__icontains=search_term) | Q(title__icontains=search_term))

        paginator = Paginator(papers,50)
        papers_page = paginator.get_page(cleaned_data['page'])
        papers_count = paginator.count
        papers_range = paginator.page_range

        return papers_page,papers_range,papers_count

    def get_context(self,form):
        if form.is_valid():
            papers_page,papers_range,papers_count = self.paper_query(form.cleaned_data)
            context = {'N_papers_total': papers_count,
                       'papers_range': papers_range,
                       'papers': papers_page,
                       'form': form}
        else:
            context = {'N_papers_total': 0,
                       'papers_range': [],
                       'papers': None,
                       'form': form}
        return context

            
    def get(self, request, *args, **kwargs):
        if request.GET:
            form = PaperSearchForm(request.GET)
            print(request.GET)
        else:
            form = PaperSearchForm({'year_min':Paper.objects.all().aggregate(Min('year'))['year__min'],
                                            'year_max':Paper.objects.all().aggregate(Max('year'))['year__max']})
        #print(form, form.is_valid())
       
        if form.is_valid():
            papers_page,papers_range,papers_count = self.paper_query(form.cleaned_data)
            context = {'N_papers_total': papers_count,
                       'papers_range': papers_range,
                       'papers': papers_page,
                       'form': form}
        else:
            context = {'N_papers_total': 0,
                       'papers_range': [],
                       'papers': None,
                       'form': form}

        return self.render_to_response(context)

    
    def post(self, request, *args, **kwargs):
        form = PaperSearchForm(data=request.POST)
        context = self.get_context(form)
        return self.render_to_response(context)

    
    
@method_decorator(login_required,name='dispatch')
class PaperDetailView(DetailView):
    model = Paper
    template_name = 'sled_papers/paper_detail.html'

    def get_queryset(self):
        return Paper.accessible_objects.all(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        qset = self.object.lenses_in_paper.annotate(discovery=F('paperlensconnection__discovery'),
                                                    model=F('paperlensconnection__model'),
                                                    classification=F('paperlensconnection__classification')
                                                    ).values('discovery','model','classification')
        labels = []
        for lens in qset:
            flags = []
            for key in lens:
                if lens[key]:
                    flags.append(key)
            labels.append(flags)
        mylabels = [ ','.join(x) for x in labels ]

        lenses = self.object.lenses_in_paper.all()
        
        lenses2 = Lenses.accessible_objects.in_ids(self.request.user,[lens.id for lens in lenses])
        if len(lenses2) != len(lenses):
            key_val = {}
            for i,lens in enumerate(lenses):
                key_val[lens.id] = i
            
            new_labels = []
            new_lenses = []
            for lens in lenses2:
                new_lenses.append( lens )
                new_labels.append( mylabels[key_val[lens.id]] )
            lenses = new_lenses
            mylabels = new_labels

            
        context['pairs'] = zip(lenses,mylabels)
        context['Nlenses'] = len(lenses)
        return context


@method_decorator(login_required,name='dispatch')
class PaperListView(ListView):
    model = Paper
    allow_empty = True
    template_name = 'sled_papers/paper_list.html'
    paginate_by = 10  # if pagination is desired

    def get_queryset(self):
        return Paper.accessible_objects.owned(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['papers'] = self.object_list
        return context

    
@method_decorator(login_required,name='dispatch')
class PaperDeleteView(BSModalDeleteView):
    model = Paper
    template_name = 'sled_papers/paper_delete.html'
    success_message = 'Success: Paper was deleted.'
    success_url = reverse_lazy('sled_papers:paper-query')
    context_object_name = 'paper'
    
    def get_queryset(self):
        return Paper.accessible_objects.owned(self.request.user)

    
@method_decorator(login_required,name='dispatch')
class PaperQuickQueryView(BSModalFormView):
    # This is a dummy view, just to launch the modal. No forms submitted. 
    template_name = 'sled_papers/paper_quick_query.html'
    form_class = PaperQuickQueryForm
    success_url = reverse_lazy('sled_users:user-profile')
    
    
@method_decorator(login_required,name='dispatch')
class PaperExportToCSVView(BSModalFormView):
    template_name = 'json_download.html'
    form_class = DownloadChooseForm

    def get_initial(self):
        paper = Paper.objects.get(pk=self.kwargs['pk'])
        lenses = paper.lenses_in_paper.all()
        ids = [ str(id) for id in lenses.values_list('id',flat=True) ]
        return {'ids': ','.join(ids),'N':len(lenses)}
    
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            ids = form.cleaned_data['ids'].split(',')
            related_to_remove = form.cleaned_data['related']
            lens_to_remove = form.cleaned_data['lens_options']
            lenses = Lenses.accessible_objects.in_ids(self.request.user,ids)
            
            serializer = LensDownSerializerAll(lenses,many=True,context={'fields_to_remove': related_to_remove + lens_to_remove})
            data = JSONRenderer().render(serializer.data)
            
            response = HttpResponse(data,content_type='application/json')
            response['Content-Disposition'] = 'attachment;filename=lenses.json'
            return response
        else:
            response = super().form_valid(form)
            return response
        
    def get_success_url(self):
        return reverse('sled_papers:paper-detail',kwargs={'pk':self.kwargs['pk']})



# View for lens Collage
@method_decorator(login_required,name='dispatch')
class PaperLensCollageView(ListView):
    model = Lenses
    allow_empty = True
    template_name = 'lenses/lens_collage.html'
    paginate_by = 50
    context_object_name = 'lenses'
    
    def get_queryset(self):
        paper = Paper.objects.get(pk=self.kwargs['pk'])
        lenses = paper.lenses_in_paper.all()
        return lenses
