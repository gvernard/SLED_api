from django import forms
from bootstrap_modal_forms.forms import BSModalForm

class CedeOwnershipForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))

class MakePrivateForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))

class DeleteObjectForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))

class ResolveDuplicatesForm(BSModalForm):
    pass

class AskPrivateAccessForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))

class AskToJoinGroupForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))

class AddDataForm(BSModalForm):
    pass

class AcceptNewUserForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))

class MergeLensesForm(forms.Form):
    mychoices = [('yes','Accept merge'),('no','Reject merge')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))
    items = forms.MultipleChoiceField(
        required=False,
        widget = forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices',None)
        super(MergeLensesForm,self).__init__(*args, **kwargs)
        if choices:
            dum = []
            for choice in choices:
                dum.append( (choice,choice) )
            self.fields['items'].choices = dum

    def clean(self):
        cleaned_data = super(MergeLensesForm,self).clean()
        response = cleaned_data.get('response')
        if  response == 'yes':
            items = cleaned_data.get('items')
            if items:
                if len(items) == 0:
                    self.add_error('__all__',"You need to select items to merge to existing lens!")
                    return




class InspectImagesBaseForm(forms.Form):
    obj_id = forms.IntegerField(required=False,widget=forms.HiddenInput())
    rejected = forms.BooleanField(required=False)
    name = forms.CharField(required=True,label='',widget=forms.HiddenInput())
    image_url = forms.CharField(required=True,label='',widget=forms.HiddenInput())
    comment = forms.CharField(required=False,label='',widget=forms.Textarea(attrs={'placeholder': 'Is there anything wrong?','rows':3,'cols':25}))
    
    def clean(self):
        cleaned_data = super(InspectImagesBaseForm,self).clean()
        if cleaned_data["rejected"] == True and cleaned_data["comment"] == '':
            self.add_error('__all__','You need to provide a justification for rejecting this image!')

                
class InspectImagesForm(forms.Form):
    mychoices = [('All','All images are accepted'),('Partial','Some images cannot be accepted'),('None','No images can be accepted')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(required=False,label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))

    def __init__(self, *args, **kwargs):
        self.N_rejected = kwargs.pop('N_rejected',None)
        super(InspectImagesForm,self).__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super(InspectImagesForm,self).clean()
        response = cleaned_data.get('response')
        response_comment = cleaned_data.get('response_comment')
        if response == 'All':
            if self.N_rejected != 0:
                self.add_error('__all__',"You have selected some images, make sure nothing is wrong!")
        elif response == "None":
            if self.N_rejected != 0:
                self.add_error('__all__',"You have selected some images, make sure nothing is wrong!")
            if not response_comment:
                self.add_error('__all__',"You need to provide an explanation for rejecting all the images!")
        else: # Partial
            if self.N_rejected == 0:
                self.add_error('__all__',"You have to select at least one image, make sure nothing is wrong!")

        return
