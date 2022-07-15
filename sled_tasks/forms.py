from django import forms
from bootstrap_modal_forms.forms import BSModalForm

class CedeOwnershipForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

class MakePrivateForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))


class DeleteObjectForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

class ResolveDuplicatesForm(BSModalForm):
    pass

class AskPrivateAccessForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

class AskToJoinGroupForm(BSModalForm):
    mychoices = [('yes','Yes'),('no','No')]
    response = forms.ChoiceField(label='Response',widget=forms.RadioSelect,choices=mychoices)
    response_comment = forms.CharField(label='',widget=forms.Textarea(attrs={'placeholder': 'Say something back'}))

class AddDataForm(BSModalForm):
    pass

