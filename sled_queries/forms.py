from django import forms
from lenses.models import SledQuery, Users
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm

class QuerySaveForm(BSModalModelForm):
    class Meta:
        model = SledQuery
        fields = ['name','description','cargo']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder':'The name of your query.'}),
            'description': forms.Textarea({'placeholder':'Provide a description for your query.','rows':3,'cols':30}),
            'cargo': forms.HiddenInput()
        }

    def clean(self):
        # Check that cargo is not empty
        if not self.cleaned_data.get('cargo'):
            self.add_error('__all__',"Your query cannot be empty!")

        # Check that at least one field was changed
        if not self.has_changed():
            self.add_error('__all__',"No changes detected!")
            
        return
