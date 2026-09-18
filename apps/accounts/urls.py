from django.urls import path
from . import views

urlpatterns = [
    path('csrf/', views.CSRFView.as_view()),
    path('register/', views.RegisterView.as_view()),
    path('login/', views.LoginView.as_view()),
    path('admin-login/', views.AdminLoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('me/', views.MeView.as_view()),
    path('change-password/', views.ChangePasswordView.as_view()),
]
