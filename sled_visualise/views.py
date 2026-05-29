from collections import defaultdict

from django.shortcuts import render
from django.urls import reverse
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.utils.decorators import method_decorator

from lenses.models import Lenses, Redshift


@method_decorator(login_required, name='dispatch')
class LensVisualiseView(ListView):
    model = Lenses
    allow_empty = True
    template_name = 'sled_visualise/lens_visualise.html'

    def get_queryset(self, ids):
        return Lenses.accessible_objects.in_ids(self.request.user, ids)

    def build_data(self, lenses):
        lens_ids = [lens.id for lens in lenses]

        # Collect the first LENS and SOURCE redshift value per lens in a single query
        z_by_lens = defaultdict(dict)
        redshifts = Redshift.accessible_objects.all(self.request.user).filter(lens_id__in=lens_ids)
        for z in redshifts:
            if z.value is not None and z.tag not in z_by_lens[z.lens_id]:
                z_by_lens[z.lens_id][z.tag] = float(z.value)

        data = []
        for lens in lenses:
            lens_types = list(lens.lens_type) if lens.lens_type else []
            source_types = list(lens.source_type) if lens.source_type else []
            lt = lens_types[0] if lens_types else ''
            st = source_types[0] if source_types else ''
            data.append({
                'id': lens.id,
                'name': lens.name,
                'ra': float(lens.ra),
                'dec': float(lens.dec),
                'lens_z': z_by_lens.get(lens.id, {}).get('LENS'),
                'source_z': z_by_lens.get(lens.id, {}).get('SOURCE'),
                'lens_type': lt,
                'source_type': st,
                'system_type': ('%s-%s' % (lt, st)) if (lt or st) else 'Unknown',
                'flag': lens.flag,
                'detail_url': reverse('lenses:lens-detail', args=[lens.id]),
            })
        return data

    def post(self, request, *args, **kwargs):
        ids = [pk for pk in self.request.POST.getlist('ids') if pk.isdigit()]
        if ids:
            lenses = self.get_queryset(ids)
            context = {'lens_data': self.build_data(lenses)}
            return render(request, self.template_name, context)
        else:
            return TemplateResponse(request, 'simple_message.html', context={'message': 'No selected lenses to visualise.'})

    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, 'simple_message.html', context={'message': 'You are accessing this page in an unauthorized way.'})
