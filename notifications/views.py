
# Create your views here.
# notifications/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.http import JsonResponse
from .models import Notification


@login_required 
def list_notifications(request):
    """List current user's notifications (simple list view)."""
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "notifications/list.html", {"notifications": qs})


# @login_required
# def mark_notification_read(request, pk):
#     """Mark a single notification read (POST)."""
#     n = get_object_or_404(Notification, pk=pk, user=request.user)
#     if request.method == "POST":
#         n.read = True
#         n.save(update_fields=["read"])
#         messages.success(request, "Notification marked as read.")
#     return redirect(request.META.get("HTTP_REFERER", reverse("dashboard")))


# @login_required
# def mark_notification_unread(request, pk):
#     n = get_object_or_404(Notification, pk=pk, user=request.user)
#     if request.method == "POST":
#         n.read = False
#         n.save(update_fields=["read"])
#         messages.success(request, "Notification marked as unread.")
#     return redirect(request.META.get("HTTP_REFERER", reverse("dashboard")))


@login_required
def mark_all_read(request):
    if request.method == "POST":
        # Mark everything as read
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        
        # If the request came from our JavaScript, send a simple 'OK' back
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'}) 
            
    # Otherwise, redirect like normal
    return redirect(request.META.get("HTTP_REFERER", reverse("dashboard"))) 
