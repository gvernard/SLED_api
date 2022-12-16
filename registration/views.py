# views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect
from .forms import RegisterForm, UserLoginForm


# Create your views here.
def register(response):
    #if someone is posting their form data, redirect them to (home for now)
    if response.method == "POST":
        print('SOMEONE IS TRYING TO REGISTER')
        form = RegisterForm(response.POST)
        if form.is_valid():
            form.save()
            print('form validated')
            return HttpResponseRedirect("../login/")
    else:
        print('someone is on the register page')
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
