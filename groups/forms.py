from django import forms
from django.core.exceptions import ValidationError
from lenses.models import SledGroup
from django.apps import apps
from bootstrap_modal_forms.forms import BSModalModelForm
    
class SledGroupForm(BSModalModelForm):
    class Meta:
        model = SledGroup
        fields = ['name','description']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your group.','rows':3,'cols':30})
        }

