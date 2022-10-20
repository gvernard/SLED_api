from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, DetailView, ListView
from lenses.models import Paper
from django.db.models import F
from django.urls import reverse_lazy

from bootstrap_modal_forms.generic import BSModalDeleteView


@method_decorator(login_required,name='dispatch')
class PaperQueryView(TemplateView):
    model = Paper
    template_name = 'sled_papers/paper_query.html'

    
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
