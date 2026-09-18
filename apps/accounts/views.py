from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import IntegrityError
from django.middleware.csrf import get_token
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, ChangePasswordSerializer


def sync_language(request, user):
    language = request.COOKIES.get('django_language', 'uz')
    if language in ('uz', 'ru', 'en') and user.preferred_language != language:
        user.preferred_language = language
        user.save(update_fields=['preferred_language'])


def safe_next(request, target, role):
    prefix = '/admin/' if role == 'ADMIN' else '/shop/'
    fallback = '/admin/dashboard/' if role == 'ADMIN' else '/shop/'
    if target.startswith(prefix) and not target.startswith('/admin/login') and url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        return target
    return fallback


class CSRFView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


class RegisterView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        if request.user.is_authenticated:
            raise PermissionDenied('Log out before registering another account.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
        except IntegrityError:
            raise serializers.ValidationError({'email': 'This email is already registered.'})
        login(request, user)
        sync_language(request, user)
        return Response({'user': UserSerializer(user).data, 'redirect': '/shop/'}, status=201)


class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'
    role = 'CUSTOMER'

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = authenticate(request, email=data['email'].strip().lower(), password=data['password'])
        if user is None or user.role != self.role:
            raise PermissionDenied('Email or password is incorrect.', code='invalid_credentials')
        login(request, user)
        sync_language(request, user)
        return Response({'user': UserSerializer(user).data, 'redirect': safe_next(request, data.get('next', ''), user.role)})


class AdminLoginView(LoginView):
    role = 'ADMIN'


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'redirect': '/'})


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        update_session_auth_hash(request, request.user)
        return Response({'changed': True})
