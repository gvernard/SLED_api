from django.db.models import Q,F
from django.conf import settings
from django.db import connection
from django.core import serializers
from django.urls import reverse,reverse_lazy

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions, status
from rest_framework.parsers import  MultiPartParser

from .serializers import UsersSerializer, GroupsSerializer, LensesUploadSerializer, ImagingDataUploadSerializer, SpectrumDataUploadSerializer, CatalogueDataUploadSerializer, PaperUploadSerializer
from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, Collection, AdminCollection, Paper

from guardian.shortcuts import assign_perm
from actstream import action

import os
import json


class UploadData(APIView):
    parser_classes = [MultiPartParser]
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self,request):
        # Here I need to check that the keys in the request are a subset of the fields used in the serializer.
        # Then, Check that each given list of keys has the same length N.

        # Get number of lenses and the keys
        print('just got some fresh data in, mmm', request.data)
        #uploaded_data = request.data.copy()
        #print(uploaded_data)
        uploaded_data = request.data.copy()
        Ndata = int(uploaded_data.pop('N')[0])
        data_type = str(uploaded_data.pop('type')[0])
        print(uploaded_data)
        keys = []
        for key,dum in uploaded_data.items():
            keys.append(key)
        #print(Ndata,keys)

        # Reshape the data ('files') in the request to create one dict per lens
        list_of_lists = []
        for key in keys:
            list_of_lists.append(uploaded_data.getlist(key))
        #print(list_of_lists)
        raw_data = []
        for i in range(0,Ndata):
            datum = {}
            for j,key in enumerate(keys):
                print(j, key, list_of_lists[j])
                datum[key] = list_of_lists[j][i]
            datum['owner'] = request.user.pk
            raw_data.append(datum)
        print(raw_data)

        if data_type == "Imaging":
            serializer = ImagingDataUploadSerializer(data=raw_data,many=True)
            print(serializer)
        elif data_type == "Spectrum":
            serializer = SpectrumDataUploadSerializer(data=raw_data,many=True)
        elif data_type == "Catalogue":
            serializer = CatalogueDataUploadSerializer(data=raw_data,many=True)
        else:
            response = {
                "Error":"Unknown data type. Valid choices are: Imaging, Spectrum, and Catalogue."
            }
            return Response(response,status=status.HTTP_406_NOT_ACCEPTABLE)
            
        print(serializer.is_valid())
        if serializer.is_valid():
            data = serializer.create(serializer.validated_data)
            # Get RA,dec separately
            ra = []
            dec = []
            for i in range(0,Ndata):
                ra.append( float(raw_data[i].get('ra')) )
                dec.append( float(raw_data[i].get('dec')) )

            # Move uploaded files to the MEDIA_ROOT/temporary/<username> directory
            if data_type != 'Catalogue':
                path = settings.MEDIA_ROOT + '/temporary/' + request.user.username + '/'
                if not os.path.exists(path):
                    os.makedirs(path)
                for i,datum in enumerate(data):
                    with open(path + datum.image.name,'wb+') as destination:
                        for chunk in datum.image.chunks():
                            destination.write(chunk)
            
            cargo = {'ra':ra,'dec':dec,'objects':serializers.serialize('json',data)}
            receiver = Users.objects.filter(id=request.user.id) # receiver must be a queryset
            mytask = ConfirmationTask.create_task(self.request.user,receiver,'AddData',cargo)
            #print(cargo['objects'])
            myurl = request.build_absolute_uri(reverse('lenses:add-data',kwargs={'pk':mytask.id}))
            response = {
                "Warning":"Data uploaded successfully. Perform the final verification step by visiting the following URL:",
                "URL": myurl
            }
            return Response(response,status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        
class UploadPapers(APIView):
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self,request):
        Paper.objects.all().delete()
        serializer = PaperUploadSerializer(data=request.data,context={'request':request},many=True)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            papers = validated_data["papers"]
            lenses_pp = validated_data["lenses_per_paper"]
            flags_pp = validated_data["flags_per_paper"]
            
            for i,paper in enumerate(papers):
                paper["owner"] = request.user
                paper["access_level"] = "PUB"
                paper_obj = Paper.objects.create(**paper)

                for j in range(0,len(lenses_pp[i])):
                    paper_obj.lenses_in_paper.add(lenses_pp[i][j],through_defaults=flags_pp[i][j])
                print(paper_obj.pk)
                
            response = "Success! Papers uploaded to the database successfully and will appear in your user profile!"
            return Response(response)
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
 
        
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
                    pub = []
                    for lens in lenses:
                        lens.save()
                        if lens.access_level == 'PRI':
                            pri.append(lens)
                        else:
                            pub.append(lens)
                    if pri:
                        assign_perm('view_lenses',request.user,pri)
                    if len(pub) > 0:
                        ad_col = AdminCollection.objects.create(item_type="Lenses",myitems=pub)
                        action.send(request.user,target=Users.getAdmin().first(),verb='Add',level='success',action_object=ad_col)
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

