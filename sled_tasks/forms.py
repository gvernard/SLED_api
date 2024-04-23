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


                
class InspectImagesForm(forms.Form):
    mychoices = [('All','All images are accepted'),('Partial','Some images cannot be accepted'),('None','No images can be accepted')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect(attrs={'class':'jb-select-radio'}),choices=mychoices)
    response_comment = forms.CharField(required=False,label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back','rows':3,}))
    items = forms.MultipleChoiceField(
        required=False,
        widget = forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices',None)
        super(InspectImagesForm,self).__init__(*args, **kwargs)
        if choices:
            dum = []
            for choice in choices:
                dum.append( (choice,choice) )
            self.fields['items'].choices = dum
    
    def clean(self):
        cleaned_data = super(InspectImagesForm,self).clean()
        response = cleaned_data.get('response')
        comment = cleaned_data.get('response_comment')
        items = cleaned_data.get('items')
        if response == 'All':
            if len(items) != 0:
                self.add_error('__all__',"You have selected some images, make sure nothing is wrong!")
            cleaned_data["response_comment"] = 'All images are accepted'
        elif response == "None":
            if len(items) != 0:
                self.add_error('__all__',"You have selected some images, make sure nothing is wrong!")
            if not comment:
                self.add_error('__all__',"You need to give a description of the problem!")
        else: # Partial
            if len(items) == 0:
                self.add_error('__all__',"You have to select at least one image, make sure nothing is wrong!")
            if not comment:
                self.add_error('__all__',"You need to give a description of the problem!")

        return
