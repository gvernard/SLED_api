from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Imaging
from django.apps import apps
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm

class ImagingUpdateForm(BSModalModelForm):
    class Meta:
        model = Imaging
        exclude = ['instrument','band','lens','owner','access_level']
        widgets = {
            'info': forms.Textarea({'rows':3,'cols':30})
        }
