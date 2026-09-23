"""OpenAPI declarations for endpoints whose request and response shapes differ."""
from django.conf import settings
from rest_framework import serializers, permissions
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from drf_spectacular.types import OpenApiTypes
from apps.accounts import views as auth
from apps.accounts.serializers import UserSerializer, RegisterSerializer, LoginSerializer, ChangePasswordSerializer
from apps.accounts.customer_views import AddressViewSet
from apps.cart import views as cart
from apps.cart.serializers import CartItemSerializer, CartMutationSerializer
from apps.dashboard import views as dashboard
from apps.inventory.views import AdjustmentView
from apps.inventory.serializers import AdjustmentSerializer, MovementSerializer
from apps.messaging import views as messaging
from apps.messaging.serializers import SendSerializer, MessageSerializer, ReadSerializer
from apps.notifications.views import NotificationViewSet, AdminNotificationViewSet
from apps.notifications.serializers import NotificationSerializer
from apps.orders import views as orders
from apps.orders.serializers import CheckoutSerializer, OrderSerializer, TransitionSerializer, ShippingAddressSerializer


class SessionCookieScheme(OpenApiAuthenticationExtension):
    target_class = 'apps.accounts.authentication.CSRFSessionAuthentication'
    name = 'SessionCookie'

    def get_security_definition(self, auto_schema):
        return {'type': 'apiKey', 'in': 'cookie', 'name': 'sessionid',
                'description': 'Django session cookie. Unsafe requests also require X-CSRFToken, including anonymous login/register.'}


class SchemaAccess(permissions.BasePermission):
    def has_permission(self, request, view):
        return settings.DEBUG or (request.user.is_authenticated and request.user.is_active and request.user.role == 'ADMIN')


Count = inline_serializer('CountResponse', {'count': serializers.IntegerField()})
Changed = inline_serializer('ChangedResponse', {'changed': serializers.BooleanField()})
Redirect = inline_serializer('RedirectResponse', {'redirect': serializers.CharField()})
AuthResult = inline_serializer('AuthResponse', {'user': UserSerializer(), 'redirect': serializers.CharField()})
CartResult = inline_serializer('CartResponse', {
    'id': serializers.IntegerField(), 'items': CartItemSerializer(many=True),
    'subtotal': serializers.DecimalField(max_digits=14, decimal_places=2)})
Quote = inline_serializer('CheckoutQuote', {
    'subtotal': serializers.DecimalField(max_digits=14, decimal_places=2),
    'shipping_fee': serializers.DecimalField(max_digits=14, decimal_places=2),
    'total': serializers.DecimalField(max_digits=14, decimal_places=2),
    'address': ShippingAddressSerializer(), 'quote_token': serializers.CharField()})
Cancel = inline_serializer('CancelOrderRequest', {'reason': serializers.CharField(required=False, allow_blank=True, max_length=500)})
FavoriteInput = inline_serializer('FavoriteRequest', {'product': serializers.IntegerField(min_value=1)})
FavoriteResult = inline_serializer('FavoriteCreated', {'id': serializers.IntegerField()})
PublicStore = inline_serializer('PublicStore', {key: serializers.CharField(allow_blank=True) for key in
    ['name', 'landing_uz', 'landing_ru', 'landing_en', 'support_phone', 'support_email']})
DashboardResult = inline_serializer('DashboardResponse', {
    **{key: serializers.IntegerField() for key in ['total_orders', 'new_orders', 'active_customers', 'active_products', 'low_stock_count', 'unread_messages']},
    'revenue': serializers.DecimalField(max_digits=14, decimal_places=2),
    'chart': serializers.ListField(child=serializers.DictField()),
    'recent_orders': OrderSerializer(many=True), 'low_stock': serializers.ListField(child=serializers.DictField())})


def annotate(view, **methods):
    extend_schema_view(**methods)(view)


annotate(auth.CSRFView, get=extend_schema(responses=inline_serializer('CSRFToken', {'csrfToken': serializers.CharField()})))
annotate(auth.RegisterView, post=extend_schema(request=RegisterSerializer, responses={201: AuthResult}))
annotate(auth.LoginView, post=extend_schema(request=LoginSerializer, responses=AuthResult))
annotate(auth.AdminLoginView, post=extend_schema(request=LoginSerializer, responses=AuthResult))
annotate(auth.LogoutView, post=extend_schema(request=None, responses=Redirect))
annotate(auth.MeView, get=extend_schema(responses=UserSerializer))
annotate(auth.ChangePasswordView, post=extend_schema(request=ChangePasswordSerializer, responses=Changed))
annotate(cart.CartView, get=extend_schema(responses=CartResult))
annotate(cart.CartItemsView, post=extend_schema(request=CartMutationSerializer, responses={201: CartResult}))
annotate(cart.CartItemDetailView,
    patch=extend_schema(request=CartMutationSerializer, responses=CartResult),
    delete=extend_schema(request=None, responses={204: None}))
annotate(cart.FavoritesView, post=extend_schema(request=FavoriteInput, responses={200: FavoriteResult, 201: FavoriteResult}))
annotate(cart.FavoriteDetailView, delete=extend_schema(request=None, responses={204: None}))
annotate(orders.PreviewView, post=extend_schema(request=CheckoutSerializer, responses=Quote))
annotate(orders.OrderViewSet,
    create=extend_schema(request=CheckoutSerializer, responses={200: OrderSerializer, 201: OrderSerializer}),
    cancel=extend_schema(request=Cancel, responses=OrderSerializer))
annotate(orders.AdminOrderViewSet, change_status=extend_schema(request=TransitionSerializer, responses=OrderSerializer))
annotate(AdjustmentView, post=extend_schema(request=AdjustmentSerializer, responses={201: MovementSerializer}))
annotate(AddressViewSet, set_default=extend_schema(request=None))
for view in [messaging.MessagesView, messaging.AdminMessagesView]:
    annotate(view, post=extend_schema(request=SendSerializer, responses={201: MessageSerializer}))
for view in [messaging.ReadView, messaging.AdminReadView]:
    annotate(view, post=extend_schema(request=ReadSerializer, responses=Count))
for view in [NotificationViewSet, AdminNotificationViewSet]:
    annotate(view,
        unread_count=extend_schema(responses=Count),
        read_all=extend_schema(request=None, responses=Count),
        read=extend_schema(request=None, responses=NotificationSerializer))
annotate(dashboard.PublicStoreView, get=extend_schema(responses=PublicStore))
annotate(dashboard.DashboardView, get=extend_schema(responses=DashboardResult))
annotate(dashboard.CustomersViewSet, set_active=extend_schema(request=dashboard.ActiveSerializer, responses=dashboard.CustomerSerializer))


def errors_hook(result, generator, request, public):
    schema = {'type': 'object', 'required': ['code', 'message'], 'properties': {
        'code': {'type': 'string'}, 'message': {'type': 'string'},
        'field_errors': {'type': 'object', 'additionalProperties': True}}}
    result.setdefault('components', {}).setdefault('schemas', {})['ApiError'] = schema
    for path, methods in result['paths'].items():
        for method, operation in methods.items():
            if method not in ('get', 'post', 'put', 'patch', 'delete'):
                continue
            for code, description in [('400', 'Validation error'), ('403', 'Session, role or CSRF failure'),
                                      ('404', 'Missing resource or resource owned by another customer'),
                                      ('409', 'Stock, state, quote or idempotency conflict'), ('429', 'Rate limit')]:
                operation['responses'].setdefault(code, {'description': description,
                    'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ApiError'}}}})
            if method not in ('get',):
                operation.setdefault('parameters', []).append({'in': 'header', 'name': 'X-CSRFToken',
                    'required': True, 'schema': {'type': 'string'}, 'description': 'Token from GET /api/v1/auth/csrf/.'})
    return result

