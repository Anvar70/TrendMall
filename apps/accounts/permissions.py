from rest_framework.permissions import BasePermission
from rest_framework.exceptions import NotAuthenticated, PermissionDenied


class RolePermission(BasePermission):
    role = None

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise NotAuthenticated('Please sign in.', code='not_authenticated')
        if not request.user.is_active or request.user.role != self.role:
            raise PermissionDenied('This page is not available for your role.', code='role_forbidden')
        return True


class IsCustomer(RolePermission):
    role = 'CUSTOMER'


class IsAdmin(RolePermission):
    role = 'ADMIN'
