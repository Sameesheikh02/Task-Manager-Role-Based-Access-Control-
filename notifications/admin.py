from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Minimal admin for Notification that fulfils project requirements:
      - view notifications
      - search/filter by user/message/read status
      - bulk actions to mark read/unread
    """
    list_display = ("short_message", "user", "task", "read", "created_at")
    list_filter = ("read", "created_at")
    search_fields = ("message", "user__email", "task__title")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("user", "message", "task")}),
        ("Status", {"fields": ("read", "created_at")}),
    )

    actions = ("mark_selected_read", "mark_selected_unread")

    def short_message(self, obj):
        # truncated message for list display
        msg = obj.message or ""
        if len(msg) > 80:
            return f"{msg[:77]}..."
        return msg
    short_message.short_description = "Message"

    def mark_selected_read(self, request, queryset):
        updated = queryset.update(read=True)
        self.message_user(request, f"{updated} notification(s) marked as read.")
    mark_selected_read.short_description = "Mark selected notifications as read"

    def mark_selected_unread(self, request, queryset):
        updated = queryset.update(read=False)
        self.message_user(request, f"{updated} notification(s) marked as unread.")
    mark_selected_unread.short_description = "Mark selected notifications as unread"
