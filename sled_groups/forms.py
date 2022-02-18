from django import forms
from lenses.models import SledGroup, Users
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm


class SledGroupForm(BSModalModelForm):
    class Meta:
        model = SledGroup
        fields = ['name','description']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your group.','rows':3,'cols':30})
        }

        
class GroupCedeOwnershipForm(BSModalModelForm):
    heir = forms.ModelChoiceField(label='User',queryset=Users.objects.all())
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the new owner.','rows':3,'cols':30}))
                
    class Meta:
        model = SledGroup
        fields = ['id','justification','heir']


class GroupAddForm(BSModalForm):
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    name = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'The name of your group.'}))
    description = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a description for your group.','rows':3,'cols':30}))
    
    def clean(self):
        # At least one User or Group must be selected
        users = self.cleaned_data.get('users')
        if not users:
            self.add_error('__all__',"Select at least one User.")

            
class GroupAddRemoveMembersForm(BSModalModelForm):
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)

    class Meta:
        model = SledGroup
        fields = ['id','users']

    def clean(self):
        # At least one User must be selected
        users = self.cleaned_data.get('users')
        if not users:
            self.add_error('__all__',"Select at least one User.")

        # If removing users then the owner must not be removed
        owner = self.instance.owner
        if owner in users:
           self.add_error('__all__',"The group owner cannot be added or removed from the group.")


class GroupLeaveForm(BSModalModelForm):
    class Meta:
        model = SledGroup
        fields = [] # no field is required
