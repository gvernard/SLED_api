from lenses.models import Users,SledGroups
from rest_framework import serializers

class UsersSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Users
        fields = ('id','username','first_name','last_name','email')


class GroupsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SledGroups
        fields = ('id','name')
