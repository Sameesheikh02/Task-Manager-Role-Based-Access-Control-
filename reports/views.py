
# Create your views here.
# reports/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
import csv
from django.db.models import Q

from .models import Report
from tasks.models import Task 


@login_required
def generate_report_and_download_csv(request):
    """
    Accept POST from admin dashboard's Generate Report form.
    Creates a Report DB row (so the admin can track it), then returns a CSV response immediately.
    """
    # only admins/managers allowed to generate reports
    user = request.user
    if not (user.is_admin or user.is_manager):
        messages.error(request, "Unauthorized to generate reports.")
        return redirect("dashboard")

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("dashboard")

    filter_user_id = request.POST.get("filter_user") or None
    date_from = request.POST.get("date_from") or None
    date_to = request.POST.get("date_to") or None
    status = request.POST.get("status") or ""

    report = Report.objects.create(
        name=f"Report by {user.email} at {timezone.now():%Y-%m-%d %H:%M}",
        created_by=user,
        filter_user_id=filter_user_id if filter_user_id else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        status=status or "",
    )

    tasks_qs = Task.objects.all()
    if report.filter_user:
        tasks_qs = tasks_qs.filter(
            Q(assignee=report.filter_user) | Q(creator=report.filter_user)
        )
    if report.status:
        tasks_qs = tasks_qs.filter(status=report.status)
    if report.date_from:
        tasks_qs = tasks_qs.filter(created_at__date__gte=report.date_from)
    if report.date_to:
        tasks_qs = tasks_qs.filter(created_at__date__lte=report.date_to)

    # prepare CSV
    filename = f"report_{report.pk}_{report.created_at:%Y%m%d%H%M%S}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "task_id",
            "title",
            "description",
            "creator",
            "assignee",
            "priority",
            "status",
            "created_at",
            "deadline",
            "completed_at",
        ]
    )

    for t in tasks_qs.order_by("-created_at"):

        # 2. HELPER LOGIC: Format names like "John Doe (john@example.com)"
        creator_str = ""
        if t.creator:
            creator_str = f"{t.creator.first_name} {t.creator.last_name} ({t.creator.email})"

        assignee_str = ""
        if t.assignee:
            assignee_str = f"{t.assignee.first_name} {t.assignee.last_name} ({t.assignee.email})"

        writer.writerow(
            [
                t.pk,
                t.title,
                t.description or "",
                creator_str,
                assignee_str,
                t.priority,
                t.status,
                t.created_at.strftime("%Y-%m-%d") if t.created_at else "",
                t.deadline.strftime("%Y-%m-%d") if t.deadline else "",
                t.completed_at.strftime("%Y-%m-%d") if t.completed_at else "",
            ]
        )
        

    # save CSV file on Report model (optional) - keep minimal: don't save file here unless requested.
    return response



