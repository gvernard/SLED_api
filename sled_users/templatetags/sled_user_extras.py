from django import template

register = template.Library() 

@register.simple_tag
def can_access(lens,user):
    return lens.has_access(user)
