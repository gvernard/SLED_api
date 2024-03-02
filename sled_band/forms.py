from django import forms
from django.core.exceptions import ValidationError

from lenses.models import Band
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm


class BandCreateForm(BSModalModelForm):
    field_order = ['name','wavelength','info']

    class Meta:
        model = Band
        fields = "__all__"
        #wavelength = FloatField(required=True, label='Wavelength', widget=NumberInput(attrs={'placeholder': 'wavelength in Angstroms'}))
        widgets = {
            'name': forms.TextInput({'placeholder':'The band name'}),
            'wavelength': forms.NumberInput(attrs={'placeholder': 'wavelength [nm]'}),
            'info': forms.Textarea({'placeholder':'Provide a description for the band.','rows':3,'cols':30}),
        }

    def clean(self):
        cleaned_data = super(BandCreateForm,self).clean()
        
        # Need to call model clean methods here to raise and catch any errors
        instance = Band(**self.cleaned_data)
        try:
            instance.full_clean()
        except ValidationError as e:
            self.add_error('__all__',"Please fix the errors below!")
            return


        
class BandUpdateForm(BSModalModelForm):
    field_order = ['name','wavelength','info']

    class Meta:
        model = Band
        fields = "__all__"
        widgets = {
            'name': forms.TextInput({'placeholder':'The band name'}),
            'wavelength': forms.TextInput({'placeholder':'wavelength [nm]'}),
            'info': forms.Textarea({'placeholder':'Provide a description for the band.','rows':3,'cols':30}),
        }

    def clean(self):
        cleaned_data = super(BandUpdateForm,self).clean()
        
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")
            return

        if self.errors:
            self.add_error('__all__',"Please fix the errors below!")
            return
            
        # Need to call model clean methods here to raise and catch any errors
        instance = Band(**self.cleaned_data)
        try:
            instance.full_clean()
        except ValidationError as e:
            errors = dict(e)
            if 'name' not in self.changed_data:
                errors.pop('name')
            if errors:
                self.add_error('__all__',"Please fix the errors below!")
                return



