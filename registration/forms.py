from django import forms
from lenses.models.user import Users
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UsernameField
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = Users
        fields = ["username", "first_name", "last_name", "email", "password1", "password2", "affiliation"]

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        # self.fields['username'].widgets.attrs.update({'class', 'field-label'})
        self.fields['username'].widget.attrs['class'] = 'field-label'
        self.fields['first_name'].widget.attrs['class'] = 'field-label'
        self.fields['last_name'].widget.attrs['class'] = 'field-label'
        self.fields['email'].widget.attrs['class'] = 'field-label'
        self.fields['password1'].widget.attrs['class'] = 'field-label'
        self.fields['password2'].widget.attrs['class'] = 'field-label'
        self.fields['affiliation'].widget.attrs['class'] = 'field-label'



class UserLoginForm(AuthenticationForm):
    class Meta:
        model = Users
        fields = ["username", "password"]

    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'field-label'
        self.fields['password'].widget.attrs['class'] = 'field-label'
