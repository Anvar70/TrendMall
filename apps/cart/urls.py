from django.urls import path
from .views import CartView, CartItemsView, FavoritesView
urlpatterns = [path('cart/', CartView.as_view()), path('cart/items/', CartItemsView.as_view()),
    path('cart/items/<int:pk>/', CartItemsView.as_view()), path('favorites/', FavoritesView.as_view()),
    path('favorites/<int:product_id>/', FavoritesView.as_view())]
