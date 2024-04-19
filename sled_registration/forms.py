from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UsernameField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from captcha.fields import CaptchaField, CaptchaTextInput

import re
import os
import time

from lenses.models.user import Users
from sled_core.slack_api_calls import get_slack_avatar

class CustomCaptchaTextInput(CaptchaTextInput):
    template_name = 'captcha_field.html'

    
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    #captcha = CaptchaField(widget=CustomCaptchaTextInput)
    
    class Meta:
        model = Users
        fields = ["username", "first_name", "last_name", "email", "password1", "password2", "affiliation", "slack_display_name", "avatar"]
        widgets = {
            "avatar": forms.HiddenInput(),
        }
        
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
        self.fields['slack_display_name'].widget.attrs['class'] = 'field-label'
        #self.fields['captcha'].widget.attrs['class'] = 'field-label'
        #self.fields['captcha'].widget.attrs['placeholder'] = 'Type in the characters from above'

    def clean_username(self):
        value = self.cleaned_data['username']
        if not re.match(r'^[0-9a-zA-Z]*$',value):
            self.add_error("username","Only alphanumeric characters are allowed in the username!")
        return value

        
    def clean(self):
        cleaned_data = super(UserCreationForm,self).clean()

        # Check that at least one field was changed
        if not self.has_changed():
            self.add_error("__all__","No changes detected!")

        if self.cleaned_data["username"] == self.cleaned_data["email"]:
            self.add_error("__all__","Your user name cannot be the same as your email address!")
            
        if "slack_display_name" in self.changed_data:
            slack_name_avatar = [{
                "slack_name": self.cleaned_data["slack_display_name"],
                "avatar": ''
            }]
            errors,flags,slack_name_avatar = get_slack_avatar(slack_name_avatar)

            if errors:
                for e in errors:
                    self.add_error(e[0],e[1])
            else:
                self.cleaned_data["avatar"] = slack_name_avatar[0]["avatar"]


        # Need to call model clean methods here to raise and catch any errors
        dum = self.cleaned_data.copy()
        dum.pop('password1',None)
        dum.pop('captcha',None)
        dum["password"] = dum.pop('password2')
        instance = Users(**dum)
        try:
            instance.full_clean()
        except ValidationError as e:
            for err in e:
                self.add_error(err[0],err[1])
            return
        
        return
    

class UserLoginForm(AuthenticationForm):
    class Meta:
        model = Users
        fields = ["username", "password"]

    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'field-label'
        self.fields['password'].widget.attrs['class'] = 'field-label'
