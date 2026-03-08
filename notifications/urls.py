from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_notifications, name='notifications_list'),
    # path('mark-read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    # path('mark-unread/<int:pk>/', views.mark_notification_unread, name='mark_notification_unread'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
] 