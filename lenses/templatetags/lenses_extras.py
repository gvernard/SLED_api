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
