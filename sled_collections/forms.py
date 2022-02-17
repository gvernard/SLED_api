from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Collection, Lenses, Users, SledGroup
from django.apps import apps
from bootstrap_modal_forms.forms import BSModalModelForm,BSModalForm


class CustomM2M(forms.ModelMultipleChoiceField):
    def label_from_instance(self,item):
        #return "%s" % item.get_absolute_url()
        return "%s" % item.__str__()

    def clean(self,item):
        return(item)

    
class CollectionForm2(BSModalModelForm):
    class Meta:
        model = Collection
        fields = ['name','description']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your collection.','rows':3,'cols':30})
        }
            
class CollectionAskAccessForm(BSModalModelForm):
    justification = forms.CharField(widget=forms.Textarea({'placeholder':'Please provide a message for the lens owners, justifying why you require access to the private objects.','rows':3,'cols':30}))

    class Meta:
        model = Collection
        fields = ['id'] 
        
class CollectionForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user',None)
        self.request = kwargs.pop('request',None)
        super(CollectionForm,self).__init__(*args, **kwargs)
        data = kwargs.get('data')
        obj_type = data['obj_type']
        ids = data['all_items'].split(',')
        qset = apps.get_model(app_label='lenses',model_name=obj_type).accessible_objects.in_ids(self.user,ids)
        self.fields["myitems"].queryset = qset

    class Meta:
        model = Collection
        fields = ['name','description']
        widgets = {
            'description': forms.Textarea({'placeholder':'Provide a description for your collection.','rows':3,'cols':30})
        }

    obj_type = forms.CharField(widget=forms.HiddenInput)
        
    # Need to define the field because gm2m has not a default input type
    myitems = CustomM2M(
        queryset=None,
        widget=forms.CheckboxSelectMultiple(attrs={'checked':'checked'})
    )
    all_items = forms.CharField(widget=forms.HiddenInput)

    def clean(self):
        cleaned_data = super(CollectionForm,self).clean()
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        
        ### Check if formset has changed.
        if not self.has_changed():
            raise ValidationError("No changes detected.")

        if 'myitems' in cleaned_data:
            if len(cleaned_data['myitems']) <= 1:
                self.add_error('myitems','More than one object required')
        else:
            self.add_error('myitems','More than one object required')


class CollectionGiveRevokeAccessForm(BSModalModelForm):
    mode = forms.CharField(widget=forms.HiddenInput())
    users = forms.ModelMultipleChoiceField(label='Users',queryset=Users.objects.all(),required=False)
    groups = forms.ModelMultipleChoiceField(label='Groups',queryset=SledGroup.objects.all(),required=False)
                
    class Meta:
        model = Collection
        fields = ['id'] # Not really used, but 'fields' is required

    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        # At least one User or Group must be selected
        users = self.cleaned_data.get('users')
        groups = self.cleaned_data.get('groups')
        if not users and not groups:
            self.add_error('__all__',"Select at least one User and/or Group.")
