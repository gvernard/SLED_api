from django.apps import apps
from django.db import models
from django.shortcuts import render
from django.views.generic import TemplateView
from lenses.forms import *
from lenses.models import Collection, Lenses, Imaging, Spectrum, Catalogue, Redshift, GenericImage, SingleObject
from collections import OrderedDict


def get_model_fields(model_name,types_to_ex,names_to_ex):
    model_ref = apps.get_model(app_label="lenses",model_name=model_name)    
    model_fields = model_ref._meta.get_fields(include_parents=False)
    fields_help = {}
    for field in model_fields:
        field_type = field.get_internal_type()
        if field_type not in types_to_ex:
            #print(field.name,field.get_internal_type())
            fields_help[field.name] = field.help_text

    for key in names_to_ex:
        fields_help.pop(key,None)

    return fields_help


def allowed_choices(model_name,field_name):
    model_ref = apps.get_model(app_label="lenses",model_name=model_name)    
    choices = [ choice[0] for choice in model_ref._meta.get_field(field_name).choices ]
    mystr = 'Allowed choices are: <br><span class="choices">' + ', '.join(choices) + '</span>'
    return mystr



class GuideView(TemplateView):
    template_name = "sled_guide/guide.html"


    def get_context_data(self, **kwargs):
        context = super(GuideView,self).get_context_data(**kwargs)



        # Instruments and bands
        instrument_desc = "The instrument with which the observation was made. See above for available choices."
        band_desc = "The band with which the observation was made. See above for available choices."

        instrument_choices = Instrument.objects.all().values_list('name',flat=True)
        bands = Band.objects.all().values_list('name',flat=True)
        band_choices = list(filter(lambda x: x not in ['clear','---------'], bands)) # removes 'clear' and '
        mydict = {
            "instrument": 'Allowed choices are: <br><span class="choices">' + ', '.join(instrument_choices) + '</span>',
            "band": 'Allowed choices are: <br><span class="choices">' + ', '.join(band_choices) + '</span>'
        }
        context["inst_band_model"] = mydict


        
        # SingleObject
        fields_help = get_model_fields('Lenses',['ForeignKey','GM2MRelation','ManyToManyField','BigAutoField'],[])
        tmp = {key: value for key, value in fields_help.items() if key in ['access_level','owner','created_at','modified_at']}
        tmp['onwer'] = 'A SLED user who will be responsible for an object, e.g. updating, deleting, etc. This is set automatically when creating/injecting objects in SLED, but it can be ceded to another user.'
        tmp = OrderedDict(reversed(tmp.items()))
        context["singleobject_model"] = tmp
        
        # Lens
        fields_help = get_model_fields('Lenses',['ForeignKey','GM2MRelation','ManyToManyField','BigAutoField'],['created_at','modified_at','access_level'])
        fields_help['flag']             += ' ' + allowed_choices('Lenses','flag')
        fields_help['image_conf']       += ' ' + allowed_choices('Lenses','image_conf')
        fields_help['lens_type']        += ' ' + allowed_choices('Lenses','lens_type')
        fields_help['source_type']      += ' ' + allowed_choices('Lenses','source_type')
        fields_help['contaminant_type'] += ' ' + allowed_choices('Lenses','contaminant_type')
        context['lens_model'] = fields_help

        # Imaging data
        fields_help = get_model_fields('Imaging',['ForeignKey','GM2MRelation','ManyToManyField','BigAutoField'],['created_at','modified_at','access_level','exists','url'])
        fields_help["instrument"] = instrument_desc
        fields_help["band"] = band_desc
        context['imaging_model'] = fields_help

        # Spectrum
        fields_help = get_model_fields('Spectrum',['ForeignKey','GM2MRelation','ManyToManyField','BigAutoField'],['created_at','modified_at','access_level','exists'])
        fields_help["instrument"] = instrument_desc
        context['spectrum_model'] = fields_help

        # Catalogue
        fields_help = get_model_fields('Catalogue',['ForeignKey','GM2MRelation','ManyToManyField','BigAutoField'],['created_at','modified_at','access_level','exists'])
        fields_help["instrument"] = instrument_desc
        fields_help["band"] = band_desc
        context['catalogue_model'] = fields_help
        
        # Redshift
        fields_help = get_model_fields('Redshift',['ForeignKey','GM2MRelation','ManyToManyField','BigAutoField'],['created_at','modified_at','access_level','reference'])
        fields_help['method'] += ' ' + allowed_choices('Redshift','method')
        context['redshift_model'] = fields_help

        # Generic Image
        fields_help = get_model_fields('GenericImage',['ForeignKey','GM2MRelation','ManyToManyField','BigAutoField'],['created_at','modified_at','access_level'])
        context['genericimage_model'] = fields_help




        ######################## QUERY FORM FIELDS ########################
        # LensQueryForm
        lens_form = LensQueryForm()
        fields_help = {}
        for field in lens_form:
            fields_help[field.name] = field.help_text
        fields_help.pop('page')
        fields_help['flag'] += ' ' + allowed_choices('Lenses','flag')
        fields_help['lens_type'] += ' ' + allowed_choices('Lenses','lens_type')
        fields_help['source_type'] += ' ' + allowed_choices('Lenses','source_type')
        fields_help['image_conf'] += ' ' + allowed_choices('Lenses','image_conf')
        context['lens_form'] = fields_help

        
        # RedshiftQueryForm
        redshift_form = RedshiftQueryForm()
        fields_help = {}
        for field in redshift_form:
            fields_help[field.name] = field.help_text
        choices = [ choice[0] for choice in redshift_form.fields['z_source_method'].choices ]
        choices = filter(len,choices) # removes empty choice
        choices_str = ', '.join(choices)
        fields_help['z_source_method'] += ' Allowed choices are: <br><span class="choices">' + choices_str + '</span>'
        fields_help['z_lens_method'] += ' Allowed choices are: <br><span class="choices">' + choices_str + '</span>'
        fields_help['z_los_method'] += ' Allowed choices are: <br><span class="choices">' + choices_str + '</span>'
        context['redshift_form'] = fields_help


        # ImagingQueryForm
        imaging_form = ImagingQueryForm()
        fields_help = {}
        for field in imaging_form:
            fields_help[field.name] = field.help_text
        fields_help['instrument_and'] += 'If True (False), then an AND (OR) clause is used to join the instruments.'
        fields_help['instrument'] = instrument_desc
        fields_help['band'] = band_desc
        fields_help['date_taken_min'] += ' Date format is: YYYY-MM-DD.'
        fields_help['date_taken_max'] += ' Date format is: YYYY-MM-DD.'
        context['imaging_form'] = fields_help


        # SpectrumQueryForm
        spectrum_form = SpectrumQueryForm()
        fields_help = {}
        for field in spectrum_form:
            fields_help[field.name] = field.help_text
        fields_help['instrument_and'] += 'If True (False), then an AND (OR) clause is used to join the instruments.'
        fields_help['instrument'] = instrument_desc
        fields_help['date_taken_min'] += ' Date format is: YYYY-MM-DD.'
        fields_help['date_taken_max'] += ' Date format is: YYYY-MM-DD.'
        context['spectrum_form'] = fields_help


        # CatalogueQueryForm
        catalogue_form = CatalogueQueryForm()
        fields_help = {}
        for field in catalogue_form:
            fields_help[field.name] = field.help_text
        fields_help['instrument_and'] += 'If True (False), then an AND (OR) clause is used to join the instruments.'
        fields_help['instrument'] = instrument_desc
        fields_help['band'] = band_desc
        fields_help['date_taken_min'] += ' Date format is: YYYY-MM-DD.'
        fields_help['date_taken_max'] += ' Date format is: YYYY-MM-DD.'
        context['catalogue_form'] = fields_help
        
        return context
