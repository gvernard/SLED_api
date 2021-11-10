from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from lenses.models import Collection

def list_collections(request):
    return HttpResponse("Here list all collections.")


def single_collection(request,collection_id):
    return HttpResponse("A specific collection.")
