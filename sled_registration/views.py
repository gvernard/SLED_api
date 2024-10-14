from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import LoginView
from django.contrib.sites.models import Site
from django.contrib import messages
from django.template.loader import get_template
from django.template import Context
from django.template.response import TemplateResponse

from .forms import RegisterForm, UserLoginForm

from lenses.models import Users, ConfirmationTask
import smtplib


class myLoginView(LoginView):
    template_name = "sled_registration/login.html"
    authentication_form = UserLoginForm
    
    def form_valid(self,form):
        username = self.request.POST["username"]
        password = self.request.POST["password"]
        user = authenticate(self.request,username=username,password=password)
        if user is not None:
            login(self.request,user)
            return HttpResponseRedirect(self.get_success_url())
        else:
            message = 'Authentication error - Please contact the administrators.'
            messages.add_message(self.request,messages.ERROR,message)
            return HttpResponseRedirect(self.request.path_info)
        


# Create your views here.
def register(response):
    #if someone is posting their form data, redirect them to (home for now)
    if response.method == "POST":
        form = RegisterForm(response.POST)
        if form.is_valid():
            candidate_user = form.save(commit=False)
            candidate_user.is_active = False
            candidate_user.save()

            #create a confirmation task for a random admin
            cargo = {}
            cargo['object_type'] = 'Users'
            cargo['object_ids'] = [candidate_user.id]
            cargo['user_admin'] = Users.selectRandomAdmin()[0].username
            ConfirmationTask.create_task(candidate_user,Users.getAdmin(),'AcceptNewUser',cargo)
            message = "The admins have been notified and will soon process your registration!"
            #messages.add_message(response,messages.SUCCESS,message)
            #return HttpResponseRedirect("../login/")
            return TemplateResponse(response,'simple_message.html',context={'message':message})
    else:
        form = RegisterForm()

    return render(response, "sled_registration/register.html", {"form":form}) 


def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = Users.objects.filter(Q(email=data))
            if associated_users.exists():
                site = Site.objects.get_current()

                for user in associated_users:
                    subject = 'SLED: Password reset'
                    html_message = get_template('emails/password_reset.html')
                    mycontext = {
                        'first_name': user.first_name,
                        'protocol': request.scheme,
                        'domain': site.domain, #site.domain, THIS HAS TO BE SET MANUALLY...
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': default_token_generator.make_token(user),
                    }
                    html_message = html_message.render(mycontext)
                    plain_message = strip_tags(html_message)

                    user_email = user.email
                    from_email = 'sled-no-reply@sled.amnh.org'
                    send_mail(subject,plain_message,from_email,[user_email],html_message=html_message)

                return redirect ("/password_reset/done/")
    password_reset_form = PasswordResetForm()
    return render(request=request, template_name="password/password_reset.html", context={"password_reset_form":password_reset_form})

