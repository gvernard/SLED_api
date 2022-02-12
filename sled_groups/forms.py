from django import forms
from django.core.exceptions import ValidationError
from lenses.models import SledGroup,Users
from django.apps import apps
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm
    
class SledGroupForm(BSModalModelForm):
    class Meta:
        model = SledGroup
        fields = ['name','description']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your group.','rows':3,'cols':30})
        }

class GroupCedeOwnershipForm(BSModalForm):
    group_id = forms.CharField(widget=forms.HiddenInput())
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    class Meta:
        fields = ['group_id','justification','heir']

class GroupAddForm(BSModalForm):
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    name = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'The name of your group.'}))
    description = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a description for your group.','rows':3,'cols':30}))
    
    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        # At least one User or Group must be selected
        users = self.cleaned_data.get('users')
        if not users:
            self.add_error('__all__',"Select at least one User.")

class GroupAddRemoveMembersForm(BSModalForm):
    mode = forms.CharField(widget=forms.HiddenInput())
    group_id = forms.CharField(widget=forms.HiddenInput())
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)

    class Meta:
        fields = ['mode','group_id','users']
