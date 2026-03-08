
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),                     # root -> landing
    path("login/", views.login_view, name="login_view"),   # used in home.html
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("add/", views.add_user, name="add_user"),
    path("<int:pk>/edit/", views.edit_user, name="edit_user"),
    path("<int:pk>/delete/", views.delete_user, name="delete_user"),
    path("about/manager/<int:pk>/", views.about_manager, name="about_manager"),
    path("about/member/<int:pk>/", views.about_member, name="about_member"),
    
]
