from django.urls import path
from . import views
urlpatterns = [path('conversation/messages/', views.MessagesView.as_view()),
    path('conversation/read/', views.ReadView.as_view()),
    path('admin/conversations/', views.ConversationsView.as_view()),
    path('admin/conversations/<int:pk>/messages/', views.AdminMessagesView.as_view()),
    path('admin/conversations/<int:pk>/read/', views.AdminReadView.as_view())]
