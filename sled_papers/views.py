from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, DetailView, ListView
from lenses.models import Paper
from django.db.models import F, Q
from django.urls import reverse_lazy
import datetime

from bootstrap_modal_forms.generic import BSModalDeleteView
from .forms import *


@method_decorator(login_required,name='dispatch')
class PaperQueryView(TemplateView):
    model = Paper
    template_name = 'sled_papers/paper_query.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PaperSearchForm()
        return context

    def get(self, request, *args, **kwargs):
        this_year = datetime.date.today().year
        context = {}
        context['form'] = PaperSearchForm(initial={'year_min':this_year})
        context['papers_search'] = Paper.objects.filter(year=this_year)
        return self.render_to_response(context)

    
    def post(self, request, *args, **kwargs):
        #context = self.get_context_data()
        context = {}
        form = PaperSearchForm(data=request.POST)
        papers = Paper.objects.all()
        if form.is_valid():
            search_term = form.cleaned_data['search_term']
            year_min = form.cleaned_data['year_min']
            year_max = form.cleaned_data['year_max']

            if year_min and year_max:
                papers = papers.filter(year__range=[year_min,year_max])
            elif year_min and not year_max:
                papers = papers.filter(year=year_min)
            elif year_max and not year_min:
                papers = papers.filter(year=year_max)
            else:
                pass
            if search_term:
                papers = papers.filter(Q(first_author__contains=search_term) | Q(title__contains=search_term))
            context['papers_search'] = papers

        context['form'] = form
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
                                                    redshift=F('paperlensconnection__redshift')
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
