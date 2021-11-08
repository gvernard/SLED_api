from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions

from .serializers import UsersSerializer, GroupsSerializer
from lenses.models import Users, SledGroup

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




