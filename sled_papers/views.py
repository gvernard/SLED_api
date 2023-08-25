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

# Third party app imports 
from bootstrap_modal_forms.utils import is_ajax
from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView

# Local app imports
from .forms import *  
from lenses.forms import DownloadForm
from lenses.models import Lenses, Paper



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
                                                    classification=F('paperlensconnection__classification'),
                                                    #redshift=F('paperlensconnection__redshift' #no longer part of this model
                                                    ).values('discovery','model','redshift','classification')
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
    template_name = 'csv_download.html'
    form_class = DownloadForm

    def get_initial(self):
        paper = Paper.objects.get(pk=self.kwargs['pk'])
        lenses = paper.lenses_in_paper.all()
        return {'ids': 'dum','N':len(lenses)}
    
    def form_valid(self,form):
        if not is_ajax(self.request.META):
            paper = Paper.objects.get(pk=self.kwargs['pk'])
            lenses = paper.lenses_in_paper.all()
                    
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment;filename=lenses.csv'
            writer = csv.writer(response)
            field_names = ['ra',
                           'dec',
                           'name',
                           'alt_name',
                           'flag_confirmed',
                           'flag_contaminant',
                           'flag_candidate',
                           'score',
                           'image_sep',
                           'z_source',
                           'z_source_secure',
                           'z_lens',
                           'z_lens_secure',
                           'info',
                           'n_img',
                           'image_conf',
                           'lens_type',
                           'source_type',
                           'contaminant_type']
            writer.writerow(field_names)
            for lens in lenses:
                writer.writerow([getattr(lens,field) for field in field_names])
            return response
        else:
            response = super().form_valid(form)
            return response
        
    def get_success_url(self):
        return reverse('sled_papers:paper-detail',kwargs={'pk':self.kwargs['pk']})

