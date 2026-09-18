from django.urls import path
from .views import InventoryView, MovementView, AdjustmentView
urlpatterns = [path('admin/inventory/', InventoryView.as_view()),
    path('admin/inventory/movements/', MovementView.as_view()),
    path('admin/inventory/<int:variant_id>/adjust/', AdjustmentView.as_view())]
