from django import template
from django.utils.safestring import mark_safe

register = template.Library() 

@register.filter(name='get_latest_action_timestamp') 
def get_latest_action_timestamp(lens):
    act = lens.get_latest_activity()
    if act:
        return act.timestamp
    else:
        return lens.created_at

@register.filter(name='get_class_name')
def get_class_name(obj):
    return obj.__class__.__name__


@register.simple_tag
def get_tab_active(fwe,fwf,name):
    if len(fwe) != 0:
        if name == fwe[0]:
            return 'show active'
        else:
            return ''

    else:
        if len(fwf) != 0:
            if name == fwf[0]:
                return 'show active'
            else:
                return ''
        else:
            if name == 'default':
                return 'show active'
            else:
                return ''


@register.simple_tag
def get_badge(fwe,fwf,name):
    text = ''
    if name in fwe:
        text = '<span class="badge badge-pill badge-danger"><img src="{% static \'icons/exclamation.svg\' %}"></span>'
    elif name in fwf:
        text = '<span class="badge badge-pill badge-success"><img src="{% static \'icons/check.svg\' %}"></span>'
    return mark_safe(text)



@register.simple_tag
def order_bands(band_dict):
    new_bands = band_dict.keys()
    mags = []
    Dmags = []
    for band in new_bands:
        mags.append( band_dict[band]['mag'] )
        Dmags.append( band_dict[band]['Dmag'] )   
    zipped = zip(new_bands,mags,Dmags)
    return zipped


@register.simple_tag
def make_range(start,end):
    print(start,end)
    return range(int(start),int(end)+1)

@register.simple_tag
def define(var):
    return var

