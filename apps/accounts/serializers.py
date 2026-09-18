import re
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import User


class StrictSerializerMixin:
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        protected = {name for name in data if name in self.fields and self.fields[name].read_only}
        if unknown or protected:
            raise serializers.ValidationError({name: 'This field cannot be submitted.' for name in unknown | protected})
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'role', 'preferred_language', 'avatar', 'date_joined', 'marketing_consent']
        read_only_fields = fields


class RegisterSerializer(StrictSerializerMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'password', 'password_confirm']
        extra_kwargs = {'email': {'validators': []}, 'phone': {'validators': []}}

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('This email is already registered.')
        return value

    def validate_phone(self, value):
        value = re.sub(r'[\s()-]', '', value)
        if value.startswith('998'):
            value = '+' + value
        from .models import phone_validator
        phone_validator(value)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        try:
            validate_password(attrs['password'], User(email=attrs['email'], full_name=attrs['full_name']))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(StrictSerializerMixin, serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)
    next = serializers.CharField(required=False, allow_blank=True)


class ChangePasswordSerializer(StrictSerializerMixin, serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({'old_password': 'Incorrect password.'})
        try:
            validate_password(attrs['new_password'], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': exc.messages})
        return attrs
