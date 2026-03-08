# tms/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('tasks/', include('tasks.urls')),        # tasks app
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),   # <-- add this (or change 'users' to your app)
]



