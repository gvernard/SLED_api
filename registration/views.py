# views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from .forms import RegisterForm, UserLoginForm


from lenses.models import Users, ConfirmationTask

# Create your views here.
def register(response):
    #if someone is posting their form data, redirect them to (home for now)
    if response.method == "POST":
        form = RegisterForm(response.POST)
        if form.is_valid():
            print(form)
            candidate_user = form.save(commit=False)
            candidate_user.is_active = False
            candidate_user.save()
            cargo = {}
            cargo['object_type'] = 'Users'
            cargo['object_ids'] = [candidate_user.id]
            cargo['user_admin'] = Users.selectRandomAdmin()[0].username
            ConfirmationTask.create_task(candidate_user,Users.getAdmin(),'AcceptNewUser',cargo)
            messages.add_message(response,messages.SUCCESS,"The admins have been notified and will soon approve your registration.")
            return HttpResponseRedirect("../login/")
    else:
        form = RegisterForm()

    return render(response, "registration/register.html", {"form":form}) 




'''
# Create your views here.
def login(response):
    print('shit')
    #if someone is posting their form data, redirect them to (home for now)
    if response.method == "POST":
        print('SOMEONE IS TRYING TO LOGIN')
        form = UserLoginForm(response.POST)
        if form.is_valid():
            form.save()
            print('form validated')
            return redirect('../') #render(response, "login.html", {"form":form}) #HttpResponseRedirect("../")
    else:
        print('someone is on the login page')
        form = UserLoginForm()

    return render(response, "login.html", {"form":form}) 
'''
