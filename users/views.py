# users/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from tasks.views import *

from .models import CustomUser
from tasks.models import Task



@require_http_methods(["GET"])
def home(request):
    """
    Render landing/home page (home.html). If authenticated -> dashboard.
    """

    return render(request, "home.html")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        email = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)
        if user is not None and user.is_active:
            login(request, user)
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                return redirect(next_url)
            if user.is_admin:
                return redirect("admin_dashboard")
            if user.is_manager:
                return redirect("manager_dashboard")
            return redirect("member_dashboard")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")


@require_http_methods(["POST"])
def logout_view(request):
    """
    Logout (POST). Redirect back to home or login_view.
    """
    if request.user.is_authenticated:
        logout(request)
    return redirect("home")   # go to landing page after logout


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        department = request.POST.get("department", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not email:
            messages.error(request, "Email is required.")
            return render(request, "register.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "register.html")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "A user with that email already exists.")
            return render(request, "register.html")

        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            department=department
        )

        messages.success(request, "Account created successfully. You can now log in.")
        return redirect("register")   # consistent name with templates

    return render(request, "register.html")


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    user = request.user
    if user.is_admin:
        return redirect("admin_dashboard")
    if user.is_manager:
        return redirect("manager_dashboard")
    return redirect("member_dashboard")

@login_required
@require_http_methods(["GET", "POST"])
def add_user(request):
    """
    Simple admin-only view to create a new user.
    Template: add_user.html
    Expects POST fields: email, password, password_confirm, first_name, last_name, role, department, is_active (optional)
    """
    if not request.user.is_admin:
        messages.error(request, "Unauthorized Access.")
        return redirect("dashboard") 

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        role = request.POST.get("role", CustomUser.ROLE_MEMBER).strip()
        department = request.POST.get("department", "").strip()
        is_active = bool(request.POST.get("is_active"))

        # basic validation
        if not email:
            messages.error(request, "Email is required.")
            return render(request, "add_user.html")
        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "add_user.html")
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "A user with that email already exists.")
            return render(request, "add_user.html")

        # create user (uses manager to hash password)
        CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            department=department,
            is_active=is_active,
        )
        messages.success(request, f"User '{email}' created.")
        return redirect("admin_dashboard")

    # GET
    return render(request, "add_user.html")


@login_required
@require_http_methods(["GET", "POST"])
def edit_user(request, pk):
    """
    Simple admin-only user edit.
    Template: edit_user.html
    POST fields: email, first_name, last_name, role, department, is_active (checkbox)
    """
    if not request.user.is_admin:
        messages.error(request, "Unauthorized Access.")
        return redirect("dashboard")

    user_obj = get_object_or_404(CustomUser, pk=pk)

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        role = request.POST.get("role", CustomUser.ROLE_MEMBER).strip()
        department = request.POST.get("department", "").strip()
        is_active = bool(request.POST.get("is_active"))

        if not email:
            messages.error(request, "Email is required.")
            return render(request, "edit_user.html", {"user_obj": user_obj})

        # Check uniqueness (allow current user)
        if CustomUser.objects.filter(email=email).exclude(pk=user_obj.pk).exists():
            messages.error(request, "Another user with that email already exists.")
            return render(request, "edit_user.html", {"user_obj": user_obj})

        # Prevent demoting the last admin? (simple guard omitted to keep it small)
        user_obj.email = email
        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.role = role
        user_obj.department = department
        user_obj.is_active = is_active
        user_obj.save()

        messages.success(request, "User updated.")
        return redirect("admin_dashboard")

    # GET -> render form
    return render(request, "edit_user.html", {"user_obj": user_obj})


@login_required
@require_http_methods(["POST"])
def delete_user(request, pk):
    """
    Simple admin-only user deletion.
    POST-only; prevents deleting the current logged-in admin themselves.
    """
    if not request.user.is_admin:
        messages.error(request, "Unauthorized Access.")
        return redirect("dashboard")

    user_obj = get_object_or_404(CustomUser, pk=pk)

    if user_obj.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("admin_dashboard")

    user_obj.delete()
    messages.success(request, "User deleted.")
    return redirect("admin_dashboard")


@login_required
@require_http_methods(["GET"])
def about_manager(request, pk):
    """Admin-facing manager detail page."""
    if not request.user.is_admin:
        messages.error(request, "Unauthorized Access.")
        return redirect("dashboard")

    manager = get_object_or_404(CustomUser, pk=pk, role=CustomUser.ROLE_MANAGER)
    created_tasks = Task.objects.filter(creator=manager).order_by("-created_at")
    ctx = {
        "manager": manager,
        "created_tasks": created_tasks,
    }
    return render(request, "about_manager.html", ctx)


@login_required
@require_http_methods(["GET"])
def about_member(request, pk):
    """Admin-facing member detail page."""
    if not request.user.is_admin:
        messages.error(request, "Unauthorized Access.")
        return redirect("dashboard")

    member = get_object_or_404(CustomUser, pk=pk, role=CustomUser.ROLE_MEMBER)
    assigned_tasks = Task.objects.filter(assignee=member).order_by("-created_at")
    pending_count = assigned_tasks.exclude(status=Task.STATUS_COMPLETED).count()
    ctx = {
        "member": member,
        "assigned_tasks": assigned_tasks,
        "pending_count": pending_count,
    }
    return render(request, "about_member.html", ctx)