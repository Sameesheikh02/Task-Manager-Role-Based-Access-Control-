from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Minimal in-app notification model for the project requirements.
    - user: recipient of the notification
    - task: optional related task
    - message: short text shown in-app
    - read: whether the user has seen the notification
    - created_at: timestamp
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    task = models.ForeignKey("tasks.Task", null=True, blank=True, on_delete=models.SET_NULL)
    message = models.CharField(max_length=255)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Notification to {self.user} — {self.message[:40]}"
