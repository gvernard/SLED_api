from lenses.models import Users, Lenses, Redshift, Imaging, Spectrum, Catalogue
from lenses.forms import *
from django.db.models import Max, Subquery, Q

def get_combined_qset(request,user): # Must be self.request.GET or self.request.POST
    lens_form = LensQueryForm(request,prefix="lens")
    redshift_form = RedshiftQueryForm(request,prefix="redshift")
    imaging_form = ImagingQueryForm(request,prefix="imaging")
    spectrum_form = SpectrumQueryForm(request,prefix="spectrum")
    catalogue_form = CatalogueQueryForm(request,prefix="catalogue")
    management_form = ManagementQueryForm(request,prefix="management",user=user)
    for form in [lens_form,imaging_form,spectrum_form,catalogue_form]:
        form.is_valid()
    qset = combined_query(lens_form.cleaned_data,imaging_form.cleaned_data,spectrum_form.cleaned_data,catalogue_form.cleaned_data,management_form.cleaned_data,user)
    ids = [str(x) for x in qset.values_list('id',flat=True)]
    return ids


def combined_query(lens_form,redshift_form,imaging_form,spectrum_form,catalogue_form,management_form,user):
    #start with available lenses
    lenses = Lenses.accessible_objects.all(user)

    if lens_form:
        #print('Lenses form has values')
        lenses = lens_search(lenses,lens_form,user)
        #print('lenses search: ',lenses)

    if redshift_form:
        #print('Redshift form has values')
        lenses = redshift_search(lenses,redshift_form,user)
        #print(len(lenses))

    if imaging_form:
        #print('Imaging form has values')
        lenses = imaging_search(lenses,imaging_form,user)
        #print(len(lenses))

    if spectrum_form:
        #print('Spectrum not empty')
        lenses = spectrum_search(lenses,spectrum_form,user)
        #print(len(lenses))

    if catalogue_form:
        #print('CATALOGUE not empty')
        lenses = catalogue_search(lenses,catalogue_form,user)
        #print(len(lenses))

    if management_form:
        #print('Management not empty')
        lenses = management_search(lenses,management_form,user)
        #print('management search: ',lenses)
        
    return lenses


def management_search(lenses,cleaned_form,user):
    conditions = Q()
    if cleaned_form.get('access_level'):
        conditions.add(Q(**{'access_level__exact':cleaned_form.get('access_level')}),Q.AND)
    if cleaned_form.get('owner'):
        conditions.add(Q(**{'owner__username__in':cleaned_form.get('owner')}),Q.AND)
    #if cleaned_form.get('collections'):
    #    conditions.add(Q(**{'items__name__in':cleaned_form.get('collections')}),Q.AND)

    collections = cleaned_form.get('collections',None)
    if collections:
        if cleaned_form.get('collections_and'): # the clean method ensures that if 'collections' is there then so is 'collections_and'
            sets = []
            for item in collections:
                sets.append( set(lenses.filter(conditions & Q(items__name=item)).values_list('id',flat=True)) )
                final = set([id for id in lenses.values_list('id',flat=True)]).intersection(*sets)
                lenses = Lenses.accessible_objects.all(user).filter(id__in=final)
        else:
            q = Q()
            for item in collections:
                q.add( Q(items__name=item), Q.OR )
            lenses = lenses.filter(conditions & q).distinct()
    else:
        lenses = lenses.filter(conditions).distinct()
    return lenses

        

def catalogue_search(lenses,cleaned_form,user):
    conditions = Q(catalogue__exists=True)
    for key,value in cleaned_form.items():
        if key not in ['instrument','instrument_and'] and value != None:
            if '_min' in key:
                conditions.add(Q(**{'catalogue__'+key.split('_min')[0]+'__gte':value}),Q.AND)
            elif '_max' in key:
                conditions.add(Q(**{'catalogue__'+key.split('_max')[0]+'__lte':value}),Q.AND)
            else:
                conditions.add(Q(**{'catalogue__'+key:value}),Q.AND)

    instrument = cleaned_form.get('instrument',None)
    if instrument:
        if cleaned_form.get('instrument_and'): # the clean method ensures that if 'instrument' is there then so is 'instrument_and'
            sets = []
            for item in instrument:
                sets.append( set(lenses.filter(conditions & Q(catalogue__instrument__name=item)).values_list('id',flat=True)) )
                final = set([id for id in lenses.values_list('id',flat=True)]).intersection(*sets)
                lenses = Lenses.accessible_objects.all(user).filter(id__in=final)
        else:
            q = Q()
            for item in instrument:
                q.add( Q(catalogue__instrument__name=item), Q.OR )
                lenses = lenses.filter(conditions & q).distinct()
    else:
        lenses = lenses.filter(conditions).distinct()
    return lenses

    
def spectrum_search(lenses,cleaned_form,user):
    conditions = Q(spectrum__exists=True)
    for key,value in cleaned_form.items():
        if key not in ['instrument','instrument_and','wavelength_min','wavelength_max'] and value != None:
            if '_min' in key:
                conditions.add(Q(**{'spectrum__'+key.split('_min')[0]+'__gte':value}),Q.AND)
            elif '_max' in key:
                conditions.add(Q(**{'spectrum__'+key.split('_max')[0]+'__lte':value}),Q.AND)
            else:
                conditions.add(Q(**{'spectrum__'+key:value}),Q.AND)

    wavelength_min = cleaned_form.get('wavelength_min',None)
    wavelength_max = cleaned_form.get('wavelength_max',None)
    if wavelength_min and wavelength_max:
        conditions.add( Q(spectrum__lambda_min__range=(wavelength_min,wavelength_max)) |
                        Q(spectrum__lambda_max__range=(wavelength_min,wavelength_max)) |
                        (Q(spectrum__lambda_min__lt=wavelength_min) & Q(spectrum__lambda_max__gt=wavelength_max))
                        ,Q.AND)
    elif wavelength_max:
        conditions.add( Q(spectrum__lambda_min__lt=wavelength_max) ,Q.AND)
    elif wavelength_min:
        conditions.add( Q(spectrum__lambda_max__gt=wavelength_min) ,Q.AND)
            
    instrument = cleaned_form.get('instrument',None)
    if instrument:
        if cleaned_form.get('instrument_and'): # the clean method ensures that if 'instrument' is there then so is 'instrument_and'
            sets = []
            for item in instrument:
                sets.append( set(lenses.filter(conditions & Q(spectrum__instrument__name=item)).values_list('id',flat=True)) )
                final = set([id for id in lenses.values_list('id',flat=True)]).intersection(*sets)
                lenses = Lenses.accessible_objects.all(user).filter(id__in=final)
        else:
            q = Q()
            for item in instrument:
                q.add( Q(spectrum__instrument__name=item), Q.OR )
            lenses = lenses.filter(conditions & q).distinct()
    else:
        lenses = lenses.filter(conditions).distinct()
    return lenses

    
def imaging_search(lenses,cleaned_form,user):
    conditions = Q(imaging__exists=True)
    for key,value in cleaned_form.items():
        #print(key, value)
        if key not in ['instrument','instrument_and'] and value != None:
            if '_min' in key:
                conditions.add(Q(**{'imaging__'+key.split('_min')[0]+'__gte':value}),Q.AND)
            elif '_max' in key:
                conditions.add(Q(**{'imaging__'+key.split('_max')[0]+'__lte':value}),Q.AND)
            else:
                conditions.add(Q(**{'imaging__'+key:value}),Q.AND)

    instrument = cleaned_form.get('instrument',None)
    #print('instrument:', instrument)
    if instrument:
        if cleaned_form.get('instrument_and'): # the clean method ensures that if 'instrument' is there then so is 'instrument_and'
            sets = []
            for item in instrument:
                sets.append( set(lenses.filter(conditions & Q(imaging__instrument__name=item)).values_list('id',flat=True)) )
                final = set([id for id in lenses.values_list('id',flat=True)]).intersection(*sets)
                lenses = Lenses.accessible_objects.all(user).filter(id__in=final)
        else:
            q = Q()
            for item in instrument:
                q.add( Q(imaging__instrument__name=item), Q.OR )
            lenses = lenses.filter(conditions & q).distinct()
    else:
        lenses = lenses.filter(conditions).distinct()
    return lenses


def redshift_search(lenses,cleaned_form,user):
    #print(cleaned_form)
    
    conditions = Q()
    if cleaned_form.get('z_source_min') or cleaned_form.get('z_source_max') or cleaned_form.get('z_source_method'):
        conditions.add(Q(**{'redshift__tag':'SOURCE'}),Q.AND)        
        if cleaned_form.get('z_source_min'):
            conditions.add(Q(**{'redshift__value__gte':float(cleaned_form.get('z_source_min'))}),Q.AND)
        if cleaned_form.get('z_source_max'):
            conditions.add(Q(**{'redshift__value__lte':float(cleaned_form.get('z_source_max'))}),Q.AND)
        if cleaned_form.get('z_source_method'):
            conditions.add(Q(**{'redshift__method':cleaned_form.get('z_source_method')}),Q.AND)
        lenses = lenses.filter(conditions).distinct()
    
    conditions = Q()
    if cleaned_form.get('z_lens_min') or cleaned_form.get('z_lens_max') or cleaned_form.get('z_lens_method'):
        conditions.add(Q(**{'redshift__tag':'LENS'}),Q.AND)        
        if cleaned_form.get('z_lens_min'):
            conditions.add(Q(**{'redshift__value__gte':float(cleaned_form.get('z_lens_min'))}),Q.AND)
        if cleaned_form.get('z_lens_max'):
            conditions.add(Q(**{'redshift__value__lte':float(cleaned_form.get('z_lens_max'))}),Q.AND)
        if cleaned_form.get('z_lens_method'):
            conditions.add(Q(**{'redshift__method':cleaned_form.get('z_lens_method')}),Q.AND)
        lenses = lenses.filter(conditions).distinct()

    conditions = Q()
    if cleaned_form.get('z_los_min') or cleaned_form.get('z_los_max') or cleaned_form.get('z_los_method'):
        conditions.add(Q(**{'redshift__tag':'LOS'}),Q.AND) 
        if cleaned_form.get('z_los_min'):
            conditions.add(Q(**{'redshift__value__gte':float(cleaned_form.get('z_los_min'))}),Q.AND)
        if cleaned_form.get('z_los_max'):
            conditions.add(Q(**{'redshift__value__lte':float(cleaned_form.get('z_los_max'))}),Q.AND)
        if cleaned_form.get('z_los_method'):
            conditions.add(Q(**{'redshift__method':cleaned_form.get('z_los_method')}),Q.AND)
        lenses = lenses.filter(conditions).distinct()
    
    return lenses


def lens_search(lenses,form,user):
    keywords = list(form.keys())
    values = [form[keyword] for keyword in keywords]

    #decide if special attention needs to be paid to the fact that the search is done over the RA=0hours line
    over_meridian = False
    if 'ra_min' in form and 'ra_max' in form:
        if float(form['ra_min']) > float(form['ra_max']):
            over_meridian = True

    #now apply the filter for each non-null entry
    for k, value in enumerate(values):
        if value!=None:
            if 'ra_' in keywords[k] and over_meridian:
                continue
            if '_min' in keywords[k]:
                args = {keywords[k].split('_min')[0]+'__gte':float(value)}
                lenses = lenses.filter(**args).order_by('ra')
            elif '_max' in keywords[k]:
                args = {keywords[k].split('_max')[0]+'__lte':float(value)}
                lenses = lenses.filter(**args).order_by('ra')

            if keywords[k] in ['lens_type', 'source_type', 'image_conf', 'flag']:
                if len(value) > 0:
                    search_params = Q()
                    for i in range(len(value)):
                        search_params = search_params | Q((keywords[k]+'__contains', value[i]))
                        if i==len(value)-1:
                            lenses = lenses.filter(search_params)
                        
    #come back to the special case where RA_min is less than 0hours
    if over_meridian:
        lenses = lenses.filter(ra__gte=form['ra_min']) | lenses.filter(ra__lte=form['ra_max'])

    if 'ra_centre' in form:
        lenses = Lenses.proximate.get_DB_neighbours_anywhere_subqset(form['ra_centre'], form['dec_centre'], lens_subqset=lenses, radius=float(form['radius'])*3600.) # No need to pass user here

    return lenses




