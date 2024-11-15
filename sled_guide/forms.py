from django import forms
from django.core.exceptions import ValidationError
from bootstrap_modal_forms.forms import BSModalForm
from sled_core.slack_api_calls import check_slack_user,invite_slack_user

'''
class SlackRegisterForm(BSModalForm):
    email = forms.EmailField(required=True,
                             label="Email address to send Slack invitation to:"
                             )
    
    def clean_email(self):
        email = self.cleaned_data["email"]
        
        errors,exists = check_slack_user(email)
        if errors:
            for e in errors:
                self.add_error(e[0],e[1])

        if exists:
            raise ValidationError('Slack user with this email address already exists!')
        
        return email
'''    
