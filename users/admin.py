# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):  
    class Meta:
        model = CustomUser
        fields = ("email", "role", "first_name", "last_name", "department")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = "__all__"


@admin.register(CustomUser)
class CustomUserAdmin(DjangoUserAdmin): 
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    
    list_display = ("email", "first_name", "last_name", "role", "department", "is_active")
    list_filter = ("role", "is_staff", "is_active", "department")
    search_fields = ("email", "first_name", "last_name") 
    ordering = ("email",)

    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "department")}),
        (_("Role & Permissions"), {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email", 
                "password1", 
                "password2", 
                "role", 
                "first_name", 
                "last_name", 
                "department", 
                "is_active", 
                "is_staff"
            )}
         ),
    )

    readonly_fields = ("last_login", "date_joined")
    list_editable = ("role", "is_active")