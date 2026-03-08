

from django.conf import settings
from django.db import models



class Report(models.Model):
    STATUS_ALL = ""
    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_ALL, "All"),
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
    ]

    name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional human-friendly name for the generated report (e.g., 'Alice - Sep 2025').",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="generated_reports",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who generated the report.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Filters used to generate the report (store them so the report can be re-downloaded/inspected)
    filter_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reports_filtered_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional: filter tasks by this assignee/user.",
    )
    date_from = models.DateField(null=True, blank=True, help_text="Optional start date filter (inclusive).")
    date_to = models.DateField(null=True, blank=True, help_text="Optional end date filter (inclusive).")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ALL, blank=True)

    # Generated CSV file (populated when exporting). Optional to keep model minimal.
    csv_file = models.FileField(upload_to="reports/", null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Report"
        verbose_name_plural = "Reports"

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.created_at:%Y-%m-%d %H:%M})"
        # fallback descriptive label
        parts = []
        if self.filter_user:
            parts.append(f"user={getattr(self.filter_user, 'email', str(self.filter_user))}")
        if self.date_from:
            parts.append(f"from={self.date_from}")
        if self.date_to:
            parts.append(f"to={self.date_to}")
        if self.status:
            parts.append(f"status={self.get_status_display()}")
        filters = ", ".join(parts) or "all tasks"
        return f"Report: {filters} — {self.created_at:%Y-%m-%d %H:%M}"
