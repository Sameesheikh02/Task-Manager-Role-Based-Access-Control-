from django.contrib import admin
from django.http import HttpResponse
import csv
from django.utils.encoding import smart_str

from .models import Report
from tasks.models import Task


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    Minimal admin for Report that fulfills project requirements:
      - view generated reports
      - filter/search by creator, status and date
      - export the report's tasks to CSV (single-report export action)
    """
    list_display = ("__str__", "created_by", "created_at", "status")
    list_filter = ("created_by", "status", "created_at")
    search_fields = ("name", "created_by__email")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    actions = ("export_selected_report_csv",)

    def export_selected_report_csv(self, request, queryset):
        """
        Admin action to export tasks for a single selected Report as CSV.
        - If multiple reports selected, admin will be shown a message asking to select one.
        - CSV includes: task id, title, description, assignee email, priority, status, deadline, created_at, completed_at
        """
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one report to export.", level="warning")
            return None

        report = queryset.first()

        # Build Task queryset according to the stored report filters
        tasks_qs = Task.objects.all()
        if report.filter_user:
            tasks_qs = tasks_qs.filter(assignee=report.filter_user)
        if report.status:
            tasks_qs = tasks_qs.filter(status=report.status)
        if report.date_from:
            tasks_qs = tasks_qs.filter(created_at__date__gte=report.date_from)
        if report.date_to:
            tasks_qs = tasks_qs.filter(created_at__date__lte=report.date_to)

        # Prepare CSV response
        filename = f"report_{report.pk}_{report.created_at:%Y%m%d%H%M%S}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        # header
        writer.writerow(
            [
                "task_id",
                "title",
                "description",
                "creator_email",
                "assignee_email",
                "priority",
                "status",
                "deadline",
                "created_at",
                "completed_at",
            ]
        )

        for t in tasks_qs.order_by("-created_at"):
            writer.writerow(
                [
                    t.pk,
                    smart_str(t.title),
                    smart_str(t.description or ""),
                    getattr(t.creator, "email", "") if t.creator else "",
                    getattr(t.assignee, "email", "") if t.assignee else "",
                    t.priority,
                    t.status,
                    t.deadline.isoformat() if t.deadline else "",
                    t.created_at.isoformat() if t.created_at else "",
                    t.completed_at.isoformat() if t.completed_at else "",
                ]
            )

        return response

    export_selected_report_csv.short_description = "Export selected report to CSV (single report only)"
