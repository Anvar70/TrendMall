from django.db.models import Count, Q, OuterRef, Subquery, Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from apps.accounts.permissions import IsAdmin
from .models import Conversation, Message
from .serializers import MessageSerializer, SendSerializer, ReadSerializer, ConversationSerializer
from .services import send_message


class ConversationMixin:
    def conversation(self):
        if self.request.user.role == 'ADMIN':
            return get_object_or_404(Conversation, pk=self.kwargs['pk'])
        return Conversation.objects.get_or_create(customer=self.request.user)[0]


class MessagesView(ConversationMixin, generics.ListAPIView):
    serializer_class = MessageSerializer
    throttle_classes = [ScopedRateThrottle]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data['read_through'] = self.conversation().messages.filter(
            sender__role=request.user.role, read_at__isnull=False).aggregate(last=Max('id'))['last'] or 0
        return response

    def get_throttles(self):
        self.throttle_scope = 'message' if self.request.method == 'POST' else None
        return super().get_throttles()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Message.objects.none()
        qs = self.conversation().messages.select_related('sender')
        after = self.request.query_params.get('after_id', '0')
        if not after.isdigit():
            raise ValidationError({'after_id': 'Use a message ID.'})
        return qs.filter(pk__gt=int(after)).order_by('id')

    def post(self, request, **kwargs):
        data = SendSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        message = send_message(self.conversation(), request.user, data.validated_data['body'])
        return Response(MessageSerializer(message).data, status=201)


class ReadView(ConversationMixin, generics.GenericAPIView):
    serializer_class = ReadSerializer

    def post(self, request, **kwargs):
        data = self.get_serializer(data=request.data)
        data.is_valid(raise_exception=True)
        conversation = self.conversation()
        last = get_object_or_404(conversation.messages, pk=data.validated_data['last_seen_message_id'])
        qs = conversation.messages.filter(pk__lte=last.pk, read_at__isnull=True)
        qs = qs.filter(sender__role='CUSTOMER') if request.user.role == 'ADMIN' else qs.filter(sender__role='ADMIN')
        return Response({'count': qs.update(read_at=timezone.now())})


class AdminMessagesView(MessagesView):
    permission_classes = [IsAdmin]


class AdminReadView(ReadView):
    permission_classes = [IsAdmin]


class ConversationsView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        latest = Message.objects.filter(conversation=OuterRef('pk')).order_by('-id').values('body')[:1]
        qs = Conversation.objects.select_related('customer').annotate(
            unread_count=Count('messages', filter=Q(messages__sender__role='CUSTOMER', messages__read_at__isnull=True)),
            last_message=Subquery(latest))
        text = self.request.query_params.get('search')
        if text:
            qs = qs.filter(Q(customer__full_name__icontains=text) | Q(customer__email__icontains=text))
        if self.request.query_params.get('unread') == 'true':
            qs = qs.filter(unread_count__gt=0)
        return qs.order_by('-updated_at', '-id')
