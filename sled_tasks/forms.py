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

