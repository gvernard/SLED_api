# views.py
from django.shortcuts import render, redirect
from .forms import RegisterForm


# Create your views here.
def register(response):
    #if someone is posting their form data, redirect them to (home for now)
    if response.method == "POST":
        form = RegisterForm(response.POST)
        print(form)
        if form.is_valid():
            form.save()
            return redirect("../")
    else:
        form = RegisterForm()

    return render(response, "registration/register.html", {"form":form}) 
