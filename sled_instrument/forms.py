from django import forms
from lenses.models import Instrument
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm


class InstrumentCreateForm(BSModalModelForm):

    class Meta:
        model = Instrument
        fields = "__all__"
        widgets = {
            'name': forms.TextInput({'placeholder':'The instrument name'}),
            'extended_name': forms.TextInput({'placeholder':'The extended name for the instrument.'}),
            'info': forms.Textarea({'placeholder':'Provide a description for the instrument.','rows':3,'cols':30}),
        }

