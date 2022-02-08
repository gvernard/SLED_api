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


class LensesUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lenses
        exclude = ['name','owner','created_at','modified_at']

    def create(self,validated_data):
        return Lenses(**validated_data)
