from django import forms
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm
from lenses.models import Users
from sled_core.slack_api_calls import get_slack_avatar
from mysite.language_check import validate_no_profanity

class UsersSearchForm(forms.Form):
    search_term = forms.CharField(required=False,
                                  max_length=100,
                                  widget=forms.TextInput({'placeholder':'User name/surname/email keyword'}))
    mychoices = [
        ('any','any'),
        ('SuperAdmin','SuperAdmin'),
        ('Admin','Admin'),
        ('Inspector','Inspector'),
    ]
    role = forms.ChoiceField(label='Role',choices=mychoices) 
    page = forms.IntegerField(required=False,widget=forms.HiddenInput())



class UserUpdateForm(BSModalModelForm):

    class Meta:
        model = Users
        fields = ["first_name", "last_name", "email","affiliation", "homepage", "info", "slack_display_name", "avatar"]
        widgets = {
            "first_name": forms.TextInput({"placeholder":"your first name"}),
            "last_name": forms.TextInput({"placeholder":"your last name"}),
            "email": forms.TextInput({"placeholder":"your email"}),
            "affiliation": forms.TextInput({"placeholder":"your affiliation"}),
            "homepage": forms.TextInput({"placeholder":"your homepage"}),
            "info": forms.Textarea({"placeholder":"your info"}),
            "slack_display_name": forms.TextInput({"placeholder":"SLACK name"}),
            "avatar": forms.HiddenInput(),
        }

    def clean_first_name(self):
        data = self.cleaned_data["first_name"]
        validate_no_profanity(data)
        return data

    def clean_last_name(self):
        data = self.cleaned_data["last_name"]
        validate_no_profanity(data)
        return data

    def clean_info(self):
        data = self.cleaned_data["info"]
        validate_no_profanity(data)
        return data

    def clean(self):
        # Check that at least one field was changed
        if not self.has_changed():
            self.add_error("__all__","No changes detected!")


        if "slack_display_name" in self.changed_data:
            slack_name_avatar = [{
                "slack_name": self.cleaned_data["slack_display_name"],
                "avatar": ''
            }]
            errors,flags,slack_name_avatar = get_slack_avatar(slack_name_avatar)
            print(errors,flags,slack_name_avatar)
            
            if errors:
                for e in errors:
                    self.add_error(e[0],e[1])
            else:
                self.cleaned_data["avatar"] = slack_name_avatar[0]["avatar"]
            
        return

