from django.db.models import Q,Value,Prefetch
from django.db.models.functions import Collate
from django.core import serializers
from django.urls import reverse
from django.forms.models import model_to_dict
from django.apps import apps
from django.core.files.storage import default_storage
from django.forms import inlineformset_factory

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions, status
from rest_framework.parsers import  MultiPartParser
from rest_framework.renderers import JSONRenderer


from .serializers import UsersSerializer, GroupsSerializer, PapersSerializer, LensesUploadSerializer, LensesUpdateSerializer, ImagingDataUploadSerializer, SpectrumDataUploadSerializer, CatalogueDataUploadSerializer, PaperUploadSerializer, CollectionUploadSerializer
from .download_serializers import LensDownSerializer,LensDownSerializerAll
from lenses.models import Users, SledGroup, Lenses, ConfirmationTask, Collection, AdminCollection, Imaging, Spectrum, Catalogue, Paper
from lenses import forms, query_utils
from guardian.shortcuts import assign_perm
from actstream import action

import json
import numpy as np
from distutils.util import strtobool
import time
import base64
from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType


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
            if 'date_taken' not in keys:
                print('No date provided...')
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

            # Move uploaded files to a temporary directory
            if data_type != 'Catalogue':
                content = datum.image.read()
                tmp_fname = 'temporary/' + self.request.user.username + '/' + datum.image.name
                default_storage.put_object(content,tmp_fname)
                            
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
        #Paper.objects.all().delete()
        print(request.data)
        serializer = PaperUploadSerializer(data=request.data,context={'request':request},many=True)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            papers = validated_data["papers"]
            lenses_pp = validated_data["lenses_per_paper"]
            flags_pp = validated_data["flags_per_paper"]

            paper_instances = []
            for i,paper in enumerate(papers):
                paper["owner"] = request.user
                paper["access_level"] = "PUB"
                paper_obj = Paper.objects.create(**paper)

                for j in range(0,len(lenses_pp[i])):
                    paper_obj.lenses_in_paper.add(lenses_pp[i][j],through_defaults=flags_pp[i][j])
                print(paper_obj.pk)
                paper_instances.append(paper_obj)
                
            ad_col = AdminCollection.objects.create(item_type="Paper",myitems=paper_instances)
            action.send(request.user,target=Users.getAdmin().first(),verb='AddHome',level='success',action_object=ad_col)
                
            response = "Success! Papers uploaded to the database successfully and will appear in your user profile!"
            return Response(response)
        else:
            print(serializer.errors)
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
 

class UploadCollection(APIView):
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self,request):
        #Paper.objects.all().delete()
        print(request.data)
        serializer = CollectionUploadSerializer(data=request.data, context={'request':request})
        if serializer.is_valid():
            validated_data = serializer.validated_data
            lenses_pc = validated_data["lenses_in_collection"]
            access_level = validated_data["access"]
            name = validated_data["name"]
            description = validated_data["description"]

            #Collection.objects.create(**collectiondat)
            mycollection = Collection(owner=self.request.user,name=name,access_level=access_level,description=description,item_type='Lenses')
            mycollection.save()
            lens_ids = Lenses.accessible_objects.in_ids(self.request.user,lenses_pc)
            mycollection.myitems = lens_ids
            mycollection.save()

            response = "Success! Collection uploaded!"
            return Response(response)
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
 

class UploadLenses(APIView):
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]


    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # Create a formset similar to the one in LensAddView
            LensFormSet = inlineformset_factory(Users, Lenses, formset=forms.BaseLensAddUpdateFormSet, form=forms.BaseLensForm, exclude=('id',), extra=0)
            
            # Prepare the data for the formset
            formatted_data = self.format_data_for_formset(data)
            myformset = LensFormSet(data=formatted_data, files=self.prepare_files(data), instance=request.user)
            print(myformset.is_valid())
            if myformset.is_valid():
                instances = myformset.save(commit=False)

                indices, neis = Lenses.proximate.get_DB_neighbours_many(instances)
                print(instances)
                if len(indices) == 0:
                    return self.save_lenses(instances, request.user)
                else:
                    return self.handle_duplicates(instances, request)
            else:
                errors = self.collect_formset_errors(myformset)
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def collect_formset_errors(self, formset):
        errors = {}
        for i, form in enumerate(formset.forms):
            if form.errors:
                errors[f'form_{i}'] = form.errors
        if formset.non_form_errors():
            errors['non_form_errors'] = formset.non_form_errors()
        return errors
    def format_data_for_formset(self, data):
        formatted_data = {'form-TOTAL_FORMS': str(len(data)),
                          'form-INITIAL_FORMS': '0',
                          'form-MAX_NUM_FORMS': ''}
        
        for i, lens in enumerate(data):
            for key, value in lens.items():
                if key in ['lens_type', 'source_type', 'image_conf'] and isinstance(value, list):
                    value = ', '.join(value)
                formatted_data[f'form-{i}-{key}'] = value

        return formatted_data

    def prepare_files(self, data):
        files = {}
        for i, lens in enumerate(data):
            if 'mugshot' in lens:
                files[f'form-{i}-mugshot'] = ContentFile(base64.b64decode(lens['mugshot']), name=lens.get('imagename', f'image_{i}.jpg'))
        return files

    def save_lenses(self, instances, user):
        messages = ['Lenses successfully added to the database!']
        pri = []
        pub = []

        for lens in instances:
            lens.owner = user
            if lens.access_level == 'PRI':
                pri.append(lens)
            else:
                lens.access_level = 'PRI'
                pub.append(lens)
            lens.save()

        assign_perm('view_lenses', user, instances)

        if pub:
            object_type = pub[0]._meta.model.__name__
            cargo = {
                'object_type': object_type,
                'object_ids': [lens.id for lens in pub],
            }
            receiver = Users.selectRandomInspector()
            mytask = ConfirmationTask.create_task(user, receiver, 'InspectImages', cargo)
            messages.append("An InspectImages task has been submitted!")

        return Response({"message": ' '.join(messages)}, status=status.HTTP_201_CREATED)

    def handle_duplicates(self, instances, request):
        for lens in instances:
            tmp_fname = f'temporary/{request.user.username}/{lens.mugshot.name}'
            default_storage.put_object(lens.mugshot.read(), tmp_fname)
            lens.mugshot.name = tmp_fname

        cargo = {'mode': 'add', 'objects': serializers.serialize('json', instances)}
        receiver = Users.objects.filter(id=request.user.id)
        mytask = ConfirmationTask.create_task(request.user, receiver, 'ResolveDuplicates', cargo)
        
        url = request.build_absolute_uri(reverse('lenses:resolve-duplicates', kwargs={'pk': mytask.id}))
        return Response({"message": "Duplicates found", "url": url}, status=status.HTTP_409_CONFLICT)

        
class GlobalSearch(APIView):
    authentication_classes = [authentication.SessionAuthentication, authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # The dict keys must match the qset dict keys below
    fields_per_model = {
        "Users": ['username','first_name','last_name','email'],
        "Lenses": ['name','alt_name','info'],
        "Collection": ['name','description'],
        "SledGroup": ['name','description'],
        "Paper": ['first_author','title'],
        "Imaging": ['info'],
        "Spectrum": ['info'],
        "Catalogue": ['info'],
    }
    
    def get(self,request):
        term = request.query_params.get('q')

        if term is not None:
            qsets = {}
            cterm = Collate(Value(term),'utf8_general_ci')
            
            user_qset = Users.objects.exclude(username__in=['AnonymousUser','admin'])
            qsets["Users"] = user_qset = user_qset.filter(Q(username__icontains=cterm) | Q(first_name__icontains=cterm) | Q(last_name__icontains=cterm) | Q(email__icontains=cterm))
            qsets["Lenses"] = Lenses.accessible_objects.all(request.user).filter(Q(name__icontains=cterm) | Q(alt_name__icontains=cterm) | Q(info__icontains=cterm))
            qsets["Collection"] = Collection.accessible_objects.all(request.user).filter(Q(name__icontains=cterm) | Q(description__icontains=cterm))
            qsets["SledGroup"] = SledGroup.accessible_objects.all(request.user).filter(Q(name__icontains=cterm) | Q(description__icontains=cterm))
            qsets["Paper"] = Paper.objects.filter(Q(first_author__icontains=cterm) | Q(title__icontains=cterm))
            qsets["Imaging"] = Imaging.accessible_objects.all(request.user).filter(info__icontains=cterm)
            qsets["Spectrum"] = Spectrum.accessible_objects.all(request.user).filter(info__icontains=cterm)
            qsets["Catalogue"] = Catalogue.accessible_objects.all(request.user).filter(info__icontains=cterm)

            items = []
            for obj_type,qset in qsets.items():
                for item in qset:
                    match = ''
                    fields = model_to_dict(item,fields=self.fields_per_model[obj_type])
                    for key,val in fields.items():
                        if val:
                            if val.find(term) != -1:
                                match = val
                                break  
                    items.append({
                        "type": apps.get_model(app_label='lenses',model_name=obj_type)._meta.verbose_name.title(),
                        "link": item.get_absolute_url(),
                        "name": item.__str__(),
                        "match": match.replace(term,"<b><u>"+term+"</u></b>")
                    })

        return Response(items)


    

class UsersAutocomplete(APIView):
    authentication_classes = [authentication.SessionAuthentication, authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self,request):
        user = request.user
        term = request.query_params.get('q')
        exclude_self = request.query_params.get('ex_self')
        excluded = ['AnonymousUser','admin']
        if exclude_self == 'true':
            excluded.append(user.username)
        queryset = Users.objects.exclude(username__in=excluded).exclude(is_active=False)
        if term is not None:
            queryset = queryset.filter(Q(username__icontains=term) | Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(email__icontains=term))
        #queryset = Users.objects.filter(username='Giorgos')
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

class PapersAutocomplete(APIView):
    def get(self,request):
        term = request.query_params.get('q')
        queryset = Paper.objects.all()
        if term is not None:
            queryset = queryset.filter(Q(cite_as__icontains=term) | Q(title__icontains=term))
        queryset.order_by('year')
        serializer = PapersSerializer(queryset,many=True)
        return Response({"papers":serializer.data})

    
class QueryLenses(APIView):
    """
    API function to query the user's lenses, simply an ra dec radius search for now, returning the closest 
    """
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request):
        user = request.user
        ra, dec, radius = float(request.data['ra']), float(request.data['dec']), float(request.data['radius'])
        lenses = Lenses.proximate.get_DB_neighbours_anywhere_user_specific(ra,dec,user,radius=radius)        
        serializer = LensDownSerializer(lenses,many=True)
        return Response({'lenses':serializer.data})

    
class QueryLensesFull(APIView):
    """
    API function to query the user's lenses, simply an ra dec radius search for now, returning the closest 
    """
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request):
        t1 = time.time()
        user = request.user        
        lens_form = forms.LensQueryForm(request.data,prefix="lens")
        redshift_form = forms.RedshiftQueryForm(request.data,prefix="redshift")
        imaging_form = forms.ImagingQueryForm(request.data,prefix="imaging")
        spectrum_form = forms.SpectrumQueryForm(request.data,prefix="spectrum")
        catalogue_form = forms.CatalogueQueryForm(request.data,prefix="catalogue")
        management_form = forms.CatalogueQueryForm(request.data,prefix="management")
        forms_with_fields = []
        forms_with_errors = []
        zipped = zip(['lenses','redshift','imaging','spectrum','catalogue','management'],[lens_form,redshift_form,imaging_form,spectrum_form,catalogue_form,management_form])
        error_messages = []
        for name,form in zipped:
            if form.is_valid():
                if form.cleaned_data:
                    forms_with_fields.append(name)
            else:
                forms_with_errors.append(name) 
                error_messages.append(form.errors)
        
        if len(forms_with_errors) > 0:
            return Response({'errors':error_messages})
        else:

            qset = query_utils.combined_query(
                lens_form.cleaned_data, redshift_form.cleaned_data, imaging_form.cleaned_data,
                spectrum_form.cleaned_data, catalogue_form.cleaned_data, management_form.cleaned_data, user)

            #print('qset finished in', time.time()-t1)
            #print('qset size: ', qset.count())


            fields = ["redshift", "imaging", "spectrum", "catalogue", "genericimage", "papers"]
            fields_to_remove = []
            for field in fields:
                key = 'download_choices-'+field
                if key in request.data.keys():
                    val = int(request.data[key])
                    if val == 0:
                        fields_to_remove.append(field)
                else:
                    fields_to_remove.append(field)
            
            serializer = LensDownSerializerAll(qset, many=True, context={'fields_to_remove':fields_to_remove})
            lensjsons = serializer.data
            print(lensjsons)

            return Response({'lenses':lensjsons, 'errors':''})


class QueryPapers(APIView):
    """
    API function to query the user's lenses, simply an ra dec radius search for now, returning the closest 
    """
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request):
        user = request.user
        ra, dec, radius = float(request.data['ra']), float(request.data['dec']), float(request.data['radius'])
        lenses = Lenses.proximate.get_DB_neighbours_anywhere_user_specific(ra,dec,user,radius=radius)
        print('searching papers')
        if lenses:
            lens = lenses[0]
            print(lens.name)
            allpapers = lens.papers(manager='objects').all()
            print(allpapers)
            lensjsons = []
            if len(allpapers)>0:
                for paper in allpapers:
                    print(paper)
                    json = model_to_dict(paper, exclude=['lenses_in_paper', 'id', 'owner', 'access_level'])
                    print('jsonised')
                    print(json)
                    lensjsons.append(json)
            else:
                lensjsons = []
        else:
            lensjsons = []
        return Response({'papers':lensjsons})


    
class UpdateLenses(APIView):
    """
    API function to update a lens; if the user then it can update immediately; if not set a notification to the owner (to be implemented..)
    """
    authentication_classes = [authentication.SessionAuthentication,authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request):
        user = request.user

        updates = list(json.loads(request.body))
        for update in updates:
            ra, dec = float(update['ra']), float(update['dec'])
            lenses = Lenses.proximate.get_DB_neighbours_anywhere_user_specific(ra, dec, user, radius=5.)
            
            lens = lenses[0]
            update_data = update.copy()
            print(update_data)
            #check for any update in parameters

            '''for key in ['lens_type', 'source_type', 'image_conf']:
                if key in update_data.keys():
                    if ',' in update_data[key]:
                        update_data[key] = [field.strip() for field in update_data[key].split(',')]
                    else:
                        update_data[key] = [update_data[key].strip()]'''

            for key in ['lens_type', 'source_type', 'image_conf']:
                if key in update_data.keys():
                    print(update_data[key])
                    if ',' in update_data[key]:
                        update_data[key] = [field.strip() for field in update_data[key].split(',')]
                        print(update_data[key])
                    else:
                        print(update_data[key])
                        update_data[key] = [update_data[key].strip()]


            print(update_data)
            print('about to serialize')
            #cannot create a lens with the same name, so let's pop it and then bring it back later
            name = False
            if 'name' in update_data.keys():
                print('Saving name for update later')
                name = update_data['name']
                update_data.pop('name')
            serializer = LensesUpdateSerializer(data=update_data, many=False)
            if serializer.is_valid():
                updated_lens = serializer.create(serializer.validated_data)
                print('managed to serialize:', updated_lens)

                for key in update_data.keys():
                    #do not update ra, dec; delete lens is likely best option, otherwise all external data-fetching tasks 
                    #will have to be restarted...
                    if key in ['ra', 'dec']:
                        continue

                    print('Might be updating', key, 'from', getattr(lens, key), 'to', getattr(updated_lens, key))
                    value = getattr(lens, key)

                    if str(type(getattr(lens, key)))=="<class 'decimal.Decimal'>":
                        value = float(value)

                    if value!=update_data[key]:
                        print('Updating', key, 'from', getattr(lens, key), 'to', getattr(updated_lens, key))
                        setattr(lens, key, getattr(updated_lens, key))

                    if name:
                       setattr(lens, 'name', name) 

                lens.save()

            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        return Response('updated values for '+str(len(updates))+' requests')

