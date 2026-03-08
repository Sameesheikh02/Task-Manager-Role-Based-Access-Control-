from django.contrib import admin
from django.utils import timezone

from tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin for Task: minimal and focused on required functionality."""

    list_display = (
        "title",
        "assignee",
        "creator",
        "priority",
        "status",
        "deadline",
        "created_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "description", "assignee__email", "creator__email")
    ordering = ("-created_at",)

    # Allow quick inline edits for these fields from the changelist
    list_editable = ("assignee", "priority", "status")

    readonly_fields = ("created_at", "updated_at", "completed_at")

    fieldsets = (
        (None, {"fields": ("title", "description")}),
        ("Assignment", {"fields": ("creator", "assignee")}),
        ("Status & Scheduling", {"fields": ("priority", "status", "deadline", "completed_at")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    actions = ("mark_selected_completed",)

    def mark_selected_completed(self, request, queryset):
        """
        Admin action to mark selected tasks as completed.
        This sets status and completed_at (required functionality).
        """
        now = timezone.now()
        updated_count = queryset.exclude(status=Task.STATUS_COMPLETED).update(
            status=Task.STATUS_COMPLETED, completed_at=now, updated_at=now
        )
        self.message_user(request, f"{updated_count} task(s) marked as completed.")
    mark_selected_completed.short_description = "Mark selected tasks as completed"

    def get_readonly_fields(self, request, obj=None):
        """
        Prevent editing creator on change view to avoid accidental reassignment of ownership.
        (creator should be set when creating; managers/admins can reassign 'assignee' instead)
        """
        ro = list(self.readonly_fields)
        if obj:  # on change view
            ro.append("creator")
        return ro
 