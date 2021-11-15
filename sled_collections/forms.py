from django import forms
from django.core.exceptions import ValidationError
from lenses.models import Collection, Lenses
from django.apps import apps

class CustomM2M(forms.ModelMultipleChoiceField):
    def label_from_instance(self,item):
        #return "%s" % item.get_absolute_url()
        return "%s" % item.__str__()

class CollectionForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user',None)
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

    # def clean(self):
    #     cleaned_data = super(CollectionForm,self).clean()

    #     if 'myitems' in self.changed_data:
    #         print('all: ',self.data)
    #         print('cleaned: ',self.cleaned_data)
    #         print('changed: ',self.changed_data)
        
    #     if 'myitems' in cleaned_data:
    #         if cleaned_data['myitems'].count() <= 1:
    #             self.add_error('myitems','More than one object required')

        
