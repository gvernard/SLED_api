from django import forms
from lenses.models import Users
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = Users
        fields = ["username", "email", "password1", "password2", "affiliation"]
