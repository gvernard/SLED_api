from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions

from .serializers import UsersSerializer
from lenses.models import Users


class UsersAutocomplete(APIView):

    def get(self,request):
        term = request.query_params.get('q')
        queryset = Users.objects.exclude(username__in=['AnonymousUser','admin'])
        if term is not None:
            queryset = queryset.filter(Q(username__icontains=term) | Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(email__icontains=term))
        queryset.order_by('last_name')

        serializer = UsersSerializer(queryset,many=True)
        return Response({"users":serializer.data})




