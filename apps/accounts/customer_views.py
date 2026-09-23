from django.db import transaction
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, Address
from .serializers import ProfileSerializer, SettingsSerializer, AddressSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user


class SettingsView(ProfileView):
    serializer_class = SettingsSerializer

    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)
        response.set_cookie('django_language', request.user.preferred_language, max_age=31536000, samesite='Lax')
        return response


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Address.objects.none()
        return Address.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        User.objects.select_for_update().get(pk=self.request.user.pk)
        default = serializer.validated_data.get('is_default', False) or not self.get_queryset().exists()
        if default:
            self.get_queryset().update(is_default=False)
        serializer.save(user=self.request.user, is_default=default)

    @transaction.atomic
    def perform_update(self, serializer):
        User.objects.select_for_update().get(pk=self.request.user.pk)
        serializer.instance = Address.objects.select_for_update().get(pk=serializer.instance.pk, user=self.request.user)
        if serializer.validated_data.get('is_default'):
            self.get_queryset().exclude(pk=serializer.instance.pk).update(is_default=False)
        serializer.save()

    @action(detail=True, methods=['post'], url_path='set-default')
    @transaction.atomic
    def set_default(self, request, pk=None):
        User.objects.select_for_update().get(pk=request.user.pk)
        address = self.get_object()
        self.get_queryset().update(is_default=False)
        address.is_default = True
        address.save(update_fields=['is_default'])
        return Response(self.get_serializer(address).data)
