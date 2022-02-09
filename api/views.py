from django.db.models import Q
from django.conf import settings
from django.db import connection
from django.core import serializers
from django.urls import reverse,reverse_lazy

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions, status
from rest_framework.parsers import  MultiPartParser

from .serializers import UsersSerializer, GroupsSerializer, LensesUploadSerializer
from lenses.models import Users, SledGroup, Lenses, ConfirmationTask

from guardian.shortcuts import assign_perm

import os
import json

class UploadLenses(APIView):
    parser_classes = [MultiPartParser]
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self,request):
        # Here I need to check that the keys in the request are a subset of the fields used in the serializer.
        # Then, Check that each given list of keys has the same length N.

        # Get number of lenses and the keys
        Nlenses = int(request.data.pop('N')[0])
        keys = []
        for key,dum in request.data.items():
            keys.append(key)
        #print(Nlenses,keys)

        # Reshape the data ('files') in the request to create one dict per lens
        list_of_lists = []
        for key in keys:
            list_of_lists.append(request.data.getlist(key))
        #print(list_of_lists)
        lenses = []
        for i in range(0,Nlenses):
            lens = {}
            for j,key in enumerate(keys):
                lens[key] = list_of_lists[j][i]
            lenses.append(lens)
        #print(lenses)

        serializer = LensesUploadSerializer(data=lenses,many=True)
        if serializer.is_valid():
            lenses = serializer.create(serializer.validated_data)
            for lens in lenses:
                lens.owner = request.user
                lens.create_name()

            indices,neis = Lenses.proximate.get_DB_neighbours_many(lenses)
            if len(indices) == 0:
                # Insert in the database
                db_vendor = connection.vendor
                if db_vendor == 'sqlite':
                    pri = []
                    for lens in lenses:
                        lens.save()
                        if lens.access_level == 'PRI':
                            pri.append(lens)
                    if pri:
                        assign_perm('view_lenses',request.user,pri)
                    #self.make_collection(instances,request.user)
                else:
                    new_lenses = Lenses.objects.bulk_create(lenses)
                    # Here I need to upload and rename the images accordingly.
                    pri = []
                    for lens in new_lenses:
                        if lens.access_level == 'PRI':
                            pri.append(lens)
                    if pri:
                        assign_perm('view_lenses',request.user,pri)
                    #self.make_collection(instances,request.user)
                response = "Success! Lenses uploaded to the database successfully!"
                return Response(response)
            else:
                # Move uploaded files to the MEDIA_ROOT/temporary/<username> directory
                path = settings.MEDIA_ROOT + '/temporary/' + request.user.username + '/'
                if not os.path.exists(path):
                    os.makedirs(path)
                for i,lens in enumerate(lenses):
                    print(type(lens.mugshot),lens.mugshot.path)
                    with open(path + lens.mugshot.name,'wb+') as destination:
                        for chunk in lens.mugshot.chunks():
                            destination.write(chunk)
                cargo = {'mode':'add','objects':serializers.serialize('json',lenses)}
                receiver = Users.objects.filter(id=request.user.id) # receiver must be a queryset
                mytask = ConfirmationTask.create_task(self.request.user,receiver,'ResolveDuplicates',cargo)

                myurl = request.build_absolute_uri(reverse('lenses:resolve-duplicates',kwargs={'pk':mytask.id}))
                response = {
                    "Error":"There were duplicates.",
                    "URL": myurl
                }
                return Response(response,status=status.HTTP_406_NOT_ACCEPTABLE)

            # response = {"data":"ok"}
            # return Response(response)
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            
        


class UsersAutocomplete(APIView):
    authentication_classes = [authentication.SessionAuthentication, authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self,request):
        user = request.user
        term = request.query_params.get('q')
        queryset = Users.objects.exclude(username__in=['AnonymousUser','admin',user.username])
        if term is not None:
            queryset = queryset.filter(Q(username__icontains=term) | Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(email__icontains=term))
        queryset.order_by('last_name')
        serializer = UsersSerializer(queryset,many=True)
        return Response({"users":serializer.data})

class GroupsAutocomplete(APIView):
    def get(self,request):
        term = request.query_params.get('q')
        queryset = SledGroup.objects.all()
        if term is not None:
            queryset = queryset.filter(name__icontains=term)
        queryset.order_by('name')
        serializer = GroupsSerializer(queryset,many=True)
        return Response({"groups":serializer.data})




