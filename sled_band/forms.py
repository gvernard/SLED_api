from django import forms
from lenses.models import Band
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm


class BandCreateForm(BSModalModelForm):

    class Meta:
        model = Band
        fields = "__all__"
        widgets = {
            'name': forms.TextInput({'placeholder':'The band name'}),
            'info': forms.Textarea({'placeholder':'Provide a description for the band.','rows':3,'cols':30}),
        }


class BandUpdateForm(BSModalModelForm):
    class Meta:
        model = Band
        fields = "__all__"
        widgets = {
            'name': forms.TextInput({'placeholder':'The band name'}),
            'info': forms.Textarea({'placeholder':'Provide a description for the band.','rows':3,'cols':30}),
        }

    def clean(self):
        # At least one User must be selected
        #users = self.cleaned_data.get('users')
        #if not users:
        #self.add_error('__all__',"WPA")

        # Check that cargo is not empty
        return