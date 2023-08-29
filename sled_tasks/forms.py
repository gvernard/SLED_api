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
        print(cleaned_data)
        response = cleaned_data.get('response')
        if  response == 'yes':
            items = cleaned_data.get('items')
            if items:
                if len(items) == 0:
                    self.add_error('__all__',"You need to select items to merge to existing lens!")
                    return
