from django import forms
from lenses.models import Band
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm


class BandCreateForm(BSModalModelForm):

    class Meta:
        model = Band
        fields = "__all__"
        #wavelength = FloatField(required=True, label='Wavelength', widget=NumberInput(attrs={'placeholder': 'wavelength in Angstroms'}))
        widgets = {
            'name': forms.TextInput({'placeholder':'The band name'}),
            'wavelength': forms.NumberInput(attrs={'placeholder': 'wavelength [nm]'}),
            'info': forms.Textarea({'placeholder':'Provide a description for the band.','rows':3,'cols':30}),
        }


class BandUpdateForm(BSModalModelForm):
    class Meta:
        model = Band
        fields = "__all__"
        widgets = {
            'name': forms.TextInput({'placeholder':'The band name'}),
            'wavelength': forms.TextInput({'placeholder':'wavelength [nm]'}),
            'info': forms.Textarea({'placeholder':'Provide a description for the band.','rows':3,'cols':30}),
        }

    def clean(self):
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")
        return
