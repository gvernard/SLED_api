from django import template

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
def get_carousel_active(fwe,fwf,name):
    if len(fwe) != 0:
        if name == fwe[0]:
            return 'active'
        else:
            return ''

    else:
        if len(fwf) != 0:
            if name == fwf[0]:
                return 'active'
            else:
                return ''
        else:
            if name == 'default':
                return 'active'
            else:
                return ''

