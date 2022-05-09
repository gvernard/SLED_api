from lenses.models import Users, SledGroup, Lenses, DataBase, Imaging, Spectrum, Catalogue
from rest_framework import serializers


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


        
### Uploading data
################################################################################
class BaseDataFileUploadListSerializer(serializers.ListSerializer):
    def validate(self,attrs):
        ### Check that no two files are the same
        duplicate_files = []
        if attrs[0].get('image'):
            for i in range(0,len(attrs)-1):
                lens1 = attrs[i]
                file1 = lens1.get('image').name
                size1 = lens1.get('image').size

                for j in range(i+1,len(attrs)):
                    lens2 = attrs[j]
                    file2 = lens2.get('image').name
                    size2 = lens1.get('image').size

                    if file1 == file2 and size1 == size2:
                        duplicate_files.append(file1)

            if len(duplicate_files) > 0:
                raise serializers.ValidationError('More than one files have the same name and size which could indicate duplicates!')

        ### Check that there is at least one matching lens per datum
        print(attrs)
        for i in range(0,len(attrs)):
            ra = attrs[i].get('ra')
            dec = attrs[i].get('dec')
            user = attrs[i].get('owner')
            print(user, user)
            mybool = Lenses.proximate.get_DB_neighbours_anywhere_user_specific(ra,dec,user=attrs[i].get('owner'))
            print(mybool)
            if not mybool:
                raise serializers.ValidationError('The given RA,dec = (%f,%f) do not correspond to any public lens in the database!' % (ra,dec))

        return attrs


class ImagingDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=7,decimal_places=4)
    dec = serializers.DecimalField(max_digits=7,decimal_places=4)

    class Meta():
        model = Imaging
        exclude = ['lens','created_at','modified_at']
        list_serializer_class = BaseDataFileUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Imaging(**validated_data)

    
class SpectrumDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=7,decimal_places=4)
    dec = serializers.DecimalField(max_digits=7,decimal_places=4)

    class Meta():
        model = Spectrum
        exclude = ['lens','created_at','modified_at']
        list_serializer_class = BaseDataFileUploadListSerializer
        
    def create(self,validated_data):
        validated_data.pop('ra')
        validated_data.pop('dec')
        return Spectrum(**validated_data)


class CatalogueDataUploadSerializer(serializers.ModelSerializer):
    ra = serializers.DecimalField(max_digits=7,decimal_places=4)
    dec = serializers.DecimalField(max_digits=7,decimal_places=4)
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
            message = 'Some lenses are too close to each other. This probably indicates a possible duplicate and submission through the API is not allowed.'
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
        exclude = ['name','owner','created_at','modified_at']
        list_serializer_class = LensesUploadListSerializer
        
    def create(self,validated_data):
        return Lenses(**validated_data)
