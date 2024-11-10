from django.db import models
from django.shortcuts import render
from django.views.generic import TemplateView
from lenses.forms import *
from lenses.models import Collection, Lenses


class GuideView(TemplateView):
    template_name = "sled_guide/guide.html"


    def get_context_data(self, **kwargs):
        context = super(GuideView,self).get_context_data(**kwargs)

        # Lens
        lens_model = Lenses._meta.get_fields(include_parents=False)
        fields_help = {}
        for field in lens_model:
            field_type = field.get_internal_type()
            if field_type not in ['ForeignKey','GM2MRelation','ManyToManyField','BigAutoField']:
                #print(field.name,field.get_internal_type())
                fields_help[field.name] = field.help_text
        key_names = ['created_at','modified_at']
        for key in key_names:
            fields_help.pop(key,None)
        context['lens_model'] = fields_help

        choices = [ choice[0] for choice in Lenses._meta.get_field('flag').choices ]
        fields_help['flag'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        choices = [ choice[0] for choice in Lenses._meta.get_field('image_conf').choices ]
        fields_help['image_conf'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        choices = [ choice[0] for choice in Lenses._meta.get_field('lens_type').choices ]
        fields_help['lens_type'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        choices = [ choice[0] for choice in Lenses._meta.get_field('source_type').choices ]
        fields_help['source_type'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        choices = [ choice[0] for choice in Lenses._meta.get_field('contaminant_type').choices ]
        fields_help['contaminant_type'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'


        
        
        # LensQueryForm
        lens_form = LensQueryForm()
        fields_help = {}
        for field in lens_form:
            fields_help[field.name] = field.help_text

        choices = [ choice[0] for choice in lens_form.fields['flag'].choices ]
        fields_help['flag'] += ' Allowed choices are: <i>' + ','.join(choices) + '</i>'

        choices = [ choice[0] for choice in lens_form.fields['lens_type'].choices ]
        fields_help['lens_type'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        choices = [ choice[0] for choice in lens_form.fields['source_type'].choices ]
        fields_help['source_type'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        choices = [ choice[0] for choice in lens_form.fields['image_conf'].choices ]
        fields_help['image_conf'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        fields_help.pop('page')
        context['lens_form'] = fields_help

        
        # RedshiftQueryForm
        redshift_form = RedshiftQueryForm()
        fields_help = {}
        for field in redshift_form:
            fields_help[field.name] = field.help_text

        choices = [ choice[0] for choice in redshift_form.fields['z_source_method'].choices ]
        choices = filter(len,choices) # removes empty choice
        choices_str = ', '.join(choices)
        fields_help['z_source_method'] += ' Allowed choices are: <i>' + choices_str + '</i>'
        fields_help['z_lens_method'] += ' Allowed choices are: <i>' + choices_str + '</i>'
        fields_help['z_los_method'] += ' Allowed choices are: <i>' + choices_str + '</i>'
        
        context['redshift_form'] = fields_help


        # ImagingQueryForm
        imaging_form = ImagingQueryForm()
        fields_help = {}
        for field in imaging_form:
            fields_help[field.name] = field.help_text

        fields_help['instrument_and'] += 'If True (False), then an AND (OR) clause is used to join the instruments.'

        choices = [ choice[1] for choice in imaging_form.fields['band'].choices ]
        choices = list(filter(lambda x: x not in ['clear','---------'], choices)) # removes 'clear' and '
        fields_help['band'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        choices = [ choice[1] for choice in imaging_form.fields['instrument'].choices ]
        fields_help['instrument'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        fields_help['date_taken_min'] += ' Date format is: YYYY-MM-DD.'
        fields_help['date_taken_max'] += ' Date format is: YYYY-MM-DD.'

        context['imaging_form'] = fields_help


        # SpectrumQueryForm
        spectrum_form = SpectrumQueryForm()
        fields_help = {}
        for field in spectrum_form:
            fields_help[field.name] = field.help_text

        fields_help['instrument_and'] += 'If True (False), then an AND (OR) clause is used to join the instruments.'

        choices = [ choice[1] for choice in spectrum_form.fields['instrument'].choices ]
        fields_help['instrument'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        fields_help['date_taken_min'] += ' Date format is: YYYY-MM-DD.'
        fields_help['date_taken_max'] += ' Date format is: YYYY-MM-DD.'

        context['spectrum_form'] = fields_help


        # CatalogueQueryForm
        catalogue_form = CatalogueQueryForm()
        fields_help = {}
        for field in catalogue_form:
            fields_help[field.name] = field.help_text

        fields_help['instrument_and'] += 'If True (False), then an AND (OR) clause is used to join the instruments.'

        choices = [ choice[1] for choice in catalogue_form.fields['band'].choices ]
        choices = list(filter(lambda x: x not in ['clear','---------'], choices)) # removes 'clear' and '
        fields_help['band'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'
        
        choices = [ choice[1] for choice in catalogue_form.fields['instrument'].choices ]
        fields_help['instrument'] += ' Allowed choices are: <i>' + ', '.join(choices) + '</i>'

        fields_help['date_taken_min'] += ' Date format is: YYYY-MM-DD.'
        fields_help['date_taken_max'] += ' Date format is: YYYY-MM-DD.'

        context['catalogue_form'] = fields_help
        
        return context
