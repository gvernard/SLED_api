import os
from django.db.models import F
from lenses.models import Users, SledGroup, Lenses, DataBase, Imaging, Spectrum, Catalogue, Paper, Collection, GenericImage, Redshift
from rest_framework import serializers, fields
from rest_framework.validators import UniqueValidator
from drf_extra_fields.fields import Base64ImageField
from itertools import chain
from django.utils import timezone
#import ads
import requests
from urllib.parse import urlencode


### Users autocomplete
################################################################################
class UsersSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Users
        fields = ('id','username','first_name','last_name','email')


        
### Groups autocomplete
################################################################################
class GroupsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SledGroup
        fields = ('id','name')


        
### Papers autocomplete
################################################################################
class PapersSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Paper
        fields = ('id','cite_as','title')        



### Uploading data
################################################################################
def check_lenses(attrs):
    lenses = []
    for i in range(0,len(attrs)):
        ra = attrs[i].get('ra')
        dec = attrs[i].get('dec')
        user = attrs[i].get('owner')
        qset = Lenses.proximate.get_DB_neighbours_anywhere(ra,dec,user=attrs[i].get('owner'))
        if qset.count() > 1:
            raise serializers.ValidationError('There are more than one lenses at the given RA,dec = (%f,%f)!' % (ra,dec))
        elif qset.count() == 1:
            attrs[i]['lens'] = qset[0]
        else:
            raise serializers.ValidationError('The given RA,dec = (%f,%f) do not correspond to any lens in the database!' % (ra,dec))
        
    return attrs
    

def check_files(attrs):
    duplicate_files = []
    for i in range(0,len(attrs)-1):
        item1 = attrs[i]
        future1 = item1.get('future')
        
        if not future1:
            
            for j in range(i+1,len(attrs)):
                item2 = attrs[j]
                future2 = item2.get('future')

                if not future2:
                    file1 = item1.get('image').name
                    size1 = item1.get('image').size
                    file2 = item2.get('image').name
                    size2 = item2.get('image').size

                    #if file1 == file2 and size1 == size2:
                    if size1 == size2:
                        duplicate_files.append(str(i)+' and '+str(j))

    for pair in duplicate_files:
        raise serializers.ValidationError('Items %s have the same size which could indicate duplicates! If not duplicates then submit separately' % pair)


    

class ImagingDataUploadListSerializer(serializers.ListSerializer):
    def validate(self,attrs):
        ### Check that there is only one matching lens per datum
        attrs = check_lenses(attrs)
                    
        ### Check that no two files are the same
        check_files(attrs)

        ### Check if Imaging data has NOT the same ra,dec,instrument, and band
        same_data = []
        for i in range(0,len(attrs)-1):
            item1 = attrs[i]
            ra1    = item1.get('ra')
            dec1   = item1.get('dec')
            instr1 = item1.get('instrument')
            band1  = item1.get('band')
            
            for j in range(i+1,len(attrs)):
                item2 = attrs[j]
                ra2    = item2.get('ra')
                dec2   = item2.get('dec')
                instr2 = item2.get('instrument')
                band2  = item2.get('band')

                if ra1 == ra2 and dec1 == dec2 and instr1 == instr2 and band1 == band2:
                    same_data.append(item1)
        if len(same_data) > 0:
            raise serializers.ValidationError('More than one imaging data found for the same lens, instrument, and band, which could indicate duplicates!')

        return attrs

        
class ImagingDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=0,max_value=360)
    dec = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=-90,max_value=90)
    image = Base64ImageField(required=False)

    class Meta():
        model = Imaging
        exclude = ['lens','created_at','modified_at']
        list_serializer_class = ImagingDataUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Imaging(**validated_data)

    def validate(self, data):
        now = timezone.now().date()
        date_taken = data.get('date_taken')
        future = data.get('future')
        if future:
            if now > date_taken:
                raise serializers.ValidationError('Date must be in the future!')
            if data.get('image'):
                raise serializers.ValidationError('You cannot submit an image for future data!')
        else:
            if now < date_taken:
                raise serializers.ValidationError('Date must be in the past!')
            if not data.get('image'):
                raise serializers.ValidationError('You must submit an image!')
                
        ### Check user limits
        if self.context['user']:
            check = self.context['user'].check_all_limits(1,self.Meta.model.__name__)
            if check["errors"]:
                for error in check["errors"]:
                    raise serializers.ValidationError(error)
        
        return data

    

    
class SpectrumDataUploadListSerializer(serializers.ListSerializer):
    def validate(self,attrs):
        ### Check that there is only one matching lens per datum
        attrs = check_lenses(attrs)
                    
        ### Check that no two files are the same
        check_files(attrs)

        ### Check if Imaging data has NOT the same ra,dec,instrument, and band
        same_data = []
        for i in range(0,len(attrs)-1):
            item1 = attrs[i]
            ra1    = item1.get('ra')
            dec1   = item1.get('dec')
            instr1 = item1.get('instrument')
            
            for j in range(i+1,len(attrs)):
                item2 = attrs[j]
                ra2    = item2.get('ra')
                dec2   = item2.get('dec')
                instr2 = item2.get('instrument')

                if ra1 == ra2 and dec1 == dec2 and instr1 == instr2:
                    same_data.append(item1)
        if len(same_data) > 0:
            raise serializers.ValidationError('More than one spectra found for the same lens and instrument, which could indicate duplicates!')

        return attrs
    
        
class SpectrumDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=0,max_value=360)
    dec = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=-90,max_value=90)
    image = Base64ImageField(required=False)

    class Meta():
        model = Spectrum
        exclude = ['lens','created_at','modified_at']
        list_serializer_class = SpectrumDataUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Spectrum(**validated_data)

    def validate(self, data):
        now = timezone.now().date()
        date_taken = data.get('date_taken')
        future = data.get('future')
        if future:
            if now > date_taken:
                raise serializers.ValidationError('Date must be in the future!')
            if data.get('image'):
                raise serializers.ValidationError('You cannot submit an image for future data!')
        else:
            if now < date_taken:
                raise serializers.ValidationError('Date must be in the past!')
            if not data.get('image'):
                raise serializers.ValidationError('You must submit an image!')
                
        ### Check user limits
        if self.context['user']:
            check = self.context['user'].check_all_limits(1,self.Meta.model.__name__)
            if check["errors"]:
                for error in check["errors"]:
                    raise serializers.ValidationError(error)
        
        return data

    

class GenericImageUploadListSerializer(serializers.ListSerializer):
    def validate(self,attrs):
        ### Check that there is only one matching lens per datum
        attrs = check_lenses(attrs)
                    
        ### Check that no two files are the same
        check_files(attrs)

        return attrs
    
        
class GenericImageUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=0,max_value=360)
    dec = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=-90,max_value=90)
    image = Base64ImageField(required=True)

    class Meta():
        model = GenericImage
        exclude = ['lens','created_at','modified_at']
        list_serializer_class = GenericImageUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return GenericImage(**validated_data)

    def validate(self, data):
        ### Check user limits
        if self.context['user']:
            check = self.context['user'].check_all_limits(1,self.Meta.model.__name__)
            if check["errors"]:
                for error in check["errors"]:
                    raise serializers.ValidationError(error)
        
        return data


    
    
class RedshiftUploadListSerializer(serializers.ListSerializer):
    def validate(self,attrs):
        ### Check that there is only one matching lens per datum
        attrs = check_lenses(attrs)

        ### Check if Redshift has NOT the same ra, dec, tag, and method
        same_data = []
        for i in range(0,len(attrs)-1):
            item1 = attrs[i]
            ra1     = item1.get('ra')
            dec1    = item1.get('dec')
            tag1    = item1.get('tag')
            method1 = item1.get('method')
            
            for j in range(i+1,len(attrs)):
                item2 = attrs[j]
                ra2     = item2.get('ra')
                dec2    = item2.get('dec')
                tag2    = item2.get('tag')
                method2 = item2.get('method')

                if ra1 == ra2 and dec1 == dec2 and tag1 == tag2 and method1 == method2:
                    same_data.append(item1)
        if len(same_data) > 0:
            raise serializers.ValidationError('More than one redshifts found for the same lens/source and method, which could indicate duplicates! If this is not a mistake, then submit separately.')

        return attrs

    
class RedshiftUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=0,max_value=360)
    dec = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=-90,max_value=90)

    class Meta():
        model = Redshift
        exclude = ['lens','created_at','modified_at']
        list_serializer_class = RedshiftUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Redshift(**validated_data)

    def validate(self, data):
        ### Check user limits
        if self.context['user']:
            check = self.context['user'].check_all_limits(1,self.Meta.model.__name__)
            if check["errors"]:
                for error in check["errors"]:
                    raise serializers.ValidationError(error)
        
        return data

    
    
class CatalogueDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=0,max_value=360)
    dec = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=-90,max_value=90)
    mag = serializers.DecimalField(max_digits=10, decimal_places=3, allow_null=True)

    class Meta():
        model = Catalogue
        exclude = ['lens','created_at','modified_at']
        #extra_kwargs = {'mag': {'allow_null': True}, 'Dmag': {'allow_null': True}} 
        #list_serializer_class = BaseDataFileUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Catalogue(**validated_data)




### Uploading collections
################################################################################
class CollectionLensSerializer(serializers.Serializer):
    ra = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=0,max_value=360)
    dec = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=-90,max_value=90)
        
    def validate(self,lens):
        user = self.context['request'].user
        ra = lens['ra']
        dec = lens['dec']
        print("individual lens validator: ",ra,dec)
        qset = Lenses.proximate.get_DB_neighbours_anywhere(ra,dec,user=user)
        N = qset.count()
        if N == 0:
            raise serializers.ValidationError('The given RA,dec = (%f,%f) do not correspond to any lens in the database!' % (ra,dec))
        elif N > 1: 
            raise serializers.ValidationError('There are more than one lenses at the given RA,dec = (%f,%f)!' % (ra,dec))
        else:
            return qset[0]


class CollectionUploadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    description = serializers.CharField(max_length=250)
    access_level = serializers.CharField(max_length=3)
    lenses = serializers.ListField(
        child=CollectionLensSerializer()
    )
    
    def create(self,validated_data):
        return Collection(**validated_data)

    #make sure there are no collections with the same exact name
    def validate_name(self, value):
        if value and Collection.objects.filter(name__exact=value).exists():
            raise serializers.ValidationError("Name already exists!")
        return value

    def validate(self,data):
        data['lenses_in_collection'] = [ lens.id for lens in data['lenses'] ]
        return data



'''    
### Uploading lenses
################################################################################
class LensesUploadListSerializer(serializers.ListSerializer):

    def validate(self,attrs):

        ### Check proximity here
        check_radius = 16 # arcsec
        proximal_lenses = []
        for i in range(0,len(attrs)-1):
            lens1 = attrs[i]
            ra1 = lens1.get('ra')
            dec1 = lens1.get('dec')

            for j in range(i+1,len(attrs)):
                lens2 = attrs[j]
                ra2 = lens2.get('ra')
                dec2 = lens2.get('dec')

                if Lenses.distance_on_sky(ra1,dec1,ra2,dec2) < check_radius:
                    proximal_lenses.append(j)

        if len(proximal_lenses) > 0:
            message = 'Some lenses are too close to each other. This probably indicates a possible duplicate and submission through the API is not allowed.'+str(proximal_lenses)
            raise serializers.ValidationError(message)

        ### Check that no two files are the same
        duplicate_files = []
        for i in range(0,len(attrs)-1):
            lens1 = attrs[i]
            file1 = lens1.get('mugshot').name
            size1 = lens1.get('mugshot').size

            for j in range(i+1,len(attrs)):
                lens2 = attrs[j]
                file2 = lens2.get('mugshot').name
                size2 = lens1.get('mugshot').size

                if file1 == file2 and size1 == size2:
                    duplicate_files.append(file1)
                    
        if len(duplicate_files) > 0:
            raise serializers.ValidationError('More than one files have the same name and size which could indicate duplicates!')

        return attrs


class LensesUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lenses
        exclude = ['id','owner','created_at','modified_at']
        list_serializer_class = LensesUploadListSerializer
        
    def create(self,validated_data):
        return Lenses(**validated_data)
'''

class LensesUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lenses
        exclude = ['id','owner','created_at','modified_at','access_level']
        optional_fields = '__all__'
        
    def create(self,validated_data):
        return Lenses(**validated_data)



### Uploading papers
################################################################################
class PaperLensSerializer(serializers.Serializer):
    ra = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=0,max_value=360)
    dec = serializers.DecimalField(max_digits=10,decimal_places=6,min_value=-90,max_value=90)
    discovery = serializers.BooleanField()
    classification = serializers.BooleanField()
    model = serializers.BooleanField()
    #redshift = serializers.BooleanField()

    def validate(self,item):
        # Restructuring of the returned item is required to use when adding a lens to a paper
        ra = item['ra']
        dec = item['dec']
        flags = {
            "discovery": item["discovery"],
            "classification": item["classification"],
            "model":item["model"]
        }
        return({'ra': ra,'dec': dec,'flags': flags})
        


class PaperUploadSerializerSynchronous(serializers.Serializer):
    bibcode = serializers.CharField(max_length=19)
    lenses = serializers.ListField(
        child=PaperLensSerializer()
    )
    

    def validate(self,paper):
        papers = [paper]
        
        ################### LENSES
        ### Check proximity of given lenses with each other
        proximal_lenses = []
        check_radius = 16 # arcsec
        ras = []
        decs = []        
        for i in range(0,len(paper['lenses'])-1):
            ra1 = paper['lenses'][i]['ra']
            dec1 = paper['lenses'][i]['dec']
            ras.append(ra1)
            decs.append(dec1)
            
            for j in range(i+1,len(paper['lenses'])):
                ra2 = paper['lenses'][j]['ra']
                dec2 = paper['lenses'][j]['dec']

                if Lenses.distance_on_sky(ra1,dec1,ra2,dec2) < check_radius:
                    proximal_lenses.append(str(i)+' and '+str(j))

        if proximal_lenses:
            errors = []
            for pair in proximal_lenses:
                errors.append('Lenses %s are too close to each other. This probably indicates a possible duplicate and submission is not allowed.' % pair)
            raise serializers.ValidationError(errors)


        ################### BIBCODES
        bibcodes = [paper['bibcode'] for paper in papers]


        ## Check for duplicate bibcodes within the uploaded data
        seen = set()
        dupl = []
        for code in bibcodes:
            if code not in seen:
                seen.add(code)
            else:
                dupl.append(code)
        if len(dupl) != 0:
            raise serializers.ValidationError('There are duplicate bibcodes: '+','.join(dupl))

        
        ## Check that bibcodes do not exist already in the database
        existing = Paper.objects.filter(bibcode__in=bibcodes).values('bibcode','cite_as')
        if len(existing) != 0:
            errors = []
            for q in existing:
                labels = q['cite_as']+' ('+q['bibcode']+')'
                errors.append('This paper exists: '+labels)
            raise serializers.ValidationError(errors)


        ## Check ADS if bibcodes are valid and fetch data that will be added to validated_data
        ## Check only at the end in order not to waste calls to the ADS API.
        token = os.environ['DJANGO_ADS_API_TOKEN']

        ## r = ads.RateLimits('SearchQuery')
        ## #q = ads.SearchQuery(bibcode="2022MNRAS.516.1347V") # random bibcode to test the remaining queries
        ## q = list(ads.SearchQuery(author="^Vernardos"))
        ## #q.execute()
        ## print('Remaining ADS api calls: ',r.limits['remaining'])
        ## if r.limits['remaining'] == 0:
        ##     raise serializers.ValidationError('Daily limit of contacting the ADS API has been reached. Try again in 24 hours!')

        not_in_ads = []
        in_ads = []
        for code in bibcodes:
            #articles = list(ads.SearchQuery(q='(alternate_bibcode:"'+code+'" OR bibcode:"'+code+'")',fl=['recid','title','year','first_author','author']))

            encoded_query = urlencode({"q": "bibcode:"+code+" OR alternate_bibcode:"+code,"fl": "title,bibcode,alternate_bibcode,id,year,first_author,author"})
            response = requests.get("https://api.adsabs.harvard.edu/v1/search/query?{}".format(encoded_query),headers={'Authorization': 'Bearer ' + token})
            response_json = response.json()
            articles = response_json["response"]["docs"]
            
            if len(articles) == 0:
                not_in_ads.append(code)
            else:
                in_ads.append(articles[0])
        if len(not_in_ads) != 0:
            if len(not_in_ads) == 1:
                raise serializers.ValidationError('This bibcode does not exist in ADS: ' + not_in_ads[0])
            else:
                raise serializers.ValidationError('These bibcodes do not exist in ADS: ' + ','.join(not_in_ads))

        ads_ids = []
        for i,paper in enumerate(papers):
            ads_ids.append(in_ads[i]["id"])
            paper["ads_id"]       = in_ads[i]["id"]
            paper["title"]        = in_ads[i]["title"][0]
            paper["year"]         = in_ads[i]["year"]
            paper["first_author"] = in_ads[i]["first_author"]
            if len(in_ads[i]["author"]) > 2:
                paper["cite_as"] = paper["first_author"] + ' et al. (' + paper["year"] + ')'
            else:
                paper["cite_as"] = ' and '.join(in_ads[i]["author"]) + ' (' + paper["year"] + ')'
        #print(ads_ids)
        
        
        ## Check that ads_id do not exist already in the database
        existing = Paper.objects.filter(ads_id__in=ads_ids).values('bibcode','cite_as')
        if len(existing) != 0:
            errors = []
            for q in existing:
                label = q['cite_as']+' ('+q['bibcode']+')'
                errors.append( 'These bibcodes already exist in SLED: '+label)
            raise serializers.ValidationError(errors)


        
        return papers[0] # This is passed to the calling API view

