from django import forms
from lenses.models import SledQuery, Users
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm

class QuerySaveForm(BSModalModelForm):
    class Meta:
        model = SledQuery
        fields = ['name','description','cargo']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your query.','rows':3,'cols':30}),
            'cargo': forms.HiddenInput()
        }

    def clean(self):
        # At least one User must be selected
        #users = self.cleaned_data.get('users')
        #if not users:
        #self.add_error('__all__',"WPA")

        # Check that cargo is not empty
        return
