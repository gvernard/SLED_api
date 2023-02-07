from django import forms
from lenses.models import Users
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm
import os
import time
import slack_sdk
from slack_sdk.errors import SlackApiError

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

    def clean(self):
        # Check that at least one field was changed
        if not self.has_changed():
            self.add_error("__all__","No changes detected!")


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
            
        return

