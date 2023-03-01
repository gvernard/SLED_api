from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UsernameField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

import re
import os
import time
import slack_sdk
from slack_sdk.errors import SlackApiError

from lenses.models.user import Users


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)

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
            SLACK_TOKEN = os.environ['DJANGO_SLACK_API_TOKEN']
            slack_client = slack_sdk.WebClient(SLACK_TOKEN)

            looper = True
            counter = 1
            while looper and counter < 10:
                try:
                    response = slack_client.users_list()
                    found = False
                    if response["ok"]:
                        for i in range(0,len(response["members"])):
                            name = response["members"][i]["profile"]["display_name"]
                            if name == self.cleaned_data["slack_display_name"]:
                                self.cleaned_data["avatar"] = response["members"][i]["profile"]["image_512"]
                                found = True
                    if not found:
                        self.add_error("__all__","User '" + self.cleaned_data["slack_display_name"] + "' does not exist in the SLED Slack workspace!")
                    looper = False
                except SlackApiError as e:
                    if e.response["error"] == "ratelimited":
                        print("Retrying connection to Slack API...")
                        time.sleep(3)
                        counter = counter + 1
                    else:
                        # Other error
                        self.add_error("__all__","Slack API error: " + e.response["error"])
                        looper = False
                        pass

            if counter >= 10:
                self.add_error("__all__","Too many requests to the Slack API. Please try again later!")


        # Need to call model clean methods here to raise and catch any errors
        dum = self.cleaned_data.copy()
        dum.pop('password1')
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
