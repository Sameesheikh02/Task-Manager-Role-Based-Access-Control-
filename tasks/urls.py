# in tasks/urls.py
from django.urls import path
from . import views 

urlpatterns = [
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("manager-dashboard/", views.manager_dashboard, name="manager_dashboard"),
    path("member-dashboard/", views.member_dashboard, name="member_dashboard"),
    path("<int:pk>/complete/", views.complete_task, name="complete_task"),
    path("<int:pk>/delete/", views.delete_task, name="delete_task"),
    path("<int:pk>/start/", views.start_task, name="start_task"),  
    # path("<int:pk>/update/", views.update_task, name="update_task"),
    path("create/", views.create_task, name="create_task"),
    path("<int:pk>/edit/", views.edit_task, name="edit_task"),

]
