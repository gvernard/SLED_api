from django import template
from django.apps import apps
import simplejson as json

from lenses.models import Users

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


@register.filter(name='get_user_link')
def get_user_link(user_pk):
    user = Users.objects.get(pk=user_pk)
    html = '<a href="' + user.get_absolute_url() + '" target="_blank">' + user.username + '</a>'
    return html

@register.filter(name='get_ad_col_url')
def get_ad_col_url(ad_col):
    if ad_col.myitems.count() == 1:
        url = ad_col.myitems.first().get_absolute_url()
    else:
        url = ad_col.get_absolute_url()
    return url

@register.filter(name='loadjson')
def loadjson(data):
    json_data = json.loads(data)
    return json_data

@register.filter(name='split')
def split(value, key):
    return value.split(key)

@register.filter(name='get_str')
def get_str(obj):
    return obj.__str__()


