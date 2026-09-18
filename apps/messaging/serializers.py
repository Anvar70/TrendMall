from rest_framework import serializers
from apps.accounts.serializers import StrictSerializerMixin
from .models import Message, Conversation


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender_name', 'sender_role', 'body', 'created_at', 'read_at']


class SendSerializer(StrictSerializerMixin, serializers.Serializer):
    body = serializers.CharField(min_length=1, max_length=2000, trim_whitespace=True)


class ReadSerializer(StrictSerializerMixin, serializers.Serializer):
    last_seen_message_id = serializers.IntegerField(min_value=1)


class ConversationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    unread_count = serializers.IntegerField(read_only=True)
    last_message = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Conversation
        fields = ['id', 'customer_name', 'customer_email', 'updated_at', 'unread_count', 'last_message']
