from django import template
from django.apps import apps


register = template.Library() 

@register.filter(name='get_name_singular')
def get_name_singular(model_name):
    model_ref = apps.get_model(app_label="lenses",model_name=model_name)
    return model_ref._meta.verbose_name.title()

@register.filter(name='get_name_plural')
def get_name_plural(model_name):
    model_ref = apps.get_model(app_label="lenses",model_name=model_name)
    return model_ref._meta.verbose_name_plural.title()

@register.simple_tag
def singular_or_plural(model_name,number):
    model_ref = apps.get_model(app_label="lenses",model_name=model_name)
    if number == 1:
        return model_ref._meta.verbose_name.title()
    else:
        return model_ref._meta.verbose_name_plural.title()
