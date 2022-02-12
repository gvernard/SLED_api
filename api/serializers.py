from lenses.models import Users, SledGroup, Lenses
from rest_framework import serializers

class UsersSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Users
        fields = ('id','username','first_name','last_name','email')


class GroupsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SledGroup
        fields = ('id','name')



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
