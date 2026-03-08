# tasks/views.py
from datetime import datetime as _dt, time as _time
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.utils.dateparse import parse_datetime, parse_date
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Task
from notifications.models import Notification
from users.models import CustomUser
from datetime import timedelta


def _get_notification_context(user):
    """Common notification context used by dashboards."""
    notifs = Notification.objects.filter(user=user).order_by("-created_at")[:10]
    unread_count = Notification.objects.filter(user=user, read=False).count()
    return {"notifications": notifs, "unread_notifications_count": unread_count}


@login_required
def admin_dashboard(request):
    """Render admin dashboard with global counts, paginated users and charts."""
    if not (request.user.is_admin or request.user.is_superuser):
        messages.error(request, "Unauthorized Access.")
        return redirect("home")

    # --- Calculations for Dashboard Statistics (Unchanged) ---
    tasks_qs = Task.objects.all()
    total_users_count = CustomUser.objects.count()
    total_managers_count = CustomUser.objects.filter(role=CustomUser.ROLE_MANAGER).count()
    total_members_count = CustomUser.objects.filter(role=CustomUser.ROLE_MEMBER).count()
    
    total_tasks_count = tasks_qs.count()
    completed_tasks_count = tasks_qs.filter(status=Task.STATUS_COMPLETED).count()
    in_progress_count = tasks_qs.filter(status=Task.STATUS_IN_PROGRESS).count()
    pending_tasks_count = tasks_qs.filter(status=Task.STATUS_PENDING).count()

    high_priority_count = tasks_qs.filter(priority=Task.PRIORITY_HIGH).count()
    medium_priority_count = tasks_qs.filter(priority=Task.PRIORITY_MEDIUM).count()
    low_priority_count = tasks_qs.filter(priority=Task.PRIORITY_LOW).count()

    # --- USER QUERY AND FILTERING LOGIC (The Fix) ---
    users_qs = CustomUser.objects.all().order_by("email")
    
    # 1. Get the search query 'q' from the URL
    query = request.GET.get('q', '').strip()

    # 2. Apply filtering if a query exists
    if query:
        # Use Q objects for an OR lookup across multiple fields
        users_qs = users_qs.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(role__icontains=query) |
            Q(department__icontains=query)
        ).distinct() # Use distinct() in case filtering causes duplicates (though unlikely for CustomUser)

    # --- PAGINATION (Now works on the filtered/unfiltered QuerySet) ---
    paginator = Paginator(users_qs, 20) 
    page_num = request.GET.get("page", 1)
    
    try:
        users = paginator.page(page_num)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        users = paginator.page(paginator.num_pages)

    # --- CONTEXT ---
    ctx = {
        # ... (Your existing counts) ...
        "total_users_count": total_users_count,
        "total_managers_count": total_managers_count,
        "total_members_count": total_members_count,
        "total_tasks_count": total_tasks_count,
        "completed_tasks_count": completed_tasks_count,
        "in_progress_count": in_progress_count,
        "pending_tasks_count": pending_tasks_count,
        "high_priority_count": high_priority_count,
        "medium_priority_count": medium_priority_count,
        "low_priority_count": low_priority_count,
        
        # This 'users' variable now contains the filtered and paginated list
        "users": users,
    }
    
    ctx.update(_get_notification_context(request.user))
    return render(request, "admin_dashboard.html", ctx)


@login_required
def manager_dashboard(request):
    if not (request.user.is_manager or request.user.is_superuser):
        messages.error(request, "Unauthorized Access.")
        return redirect("home")

    # 2. Get Manager's Department
    manager = request.user 
    manager_dept = manager.department

    # 3. MAIN FILTER LOGIC
    # We filter tasks that match TWO conditions:
    # A. The Creator is the logged-in Manager (assigned by me)
    # B. The Assignee belongs to the Manager's Department (to my dept members)
    team_tasks_qs = Task.objects.filter(
        creator=manager,
        assignee__department=manager_dept
    ).select_related('assignee', 'creator')

    
    team_tasks_qs = Task.objects.filter(creator=manager).filter(
        Q(assignee__department=manager_dept) | Q(assignee__isnull=True)
    )

    # 4. Calculate Chart Data (Based on the filtered list)
    high_count = team_tasks_qs.filter(priority='high').count()
    medium_count = team_tasks_qs.filter(priority='medium').count()
    low_count = team_tasks_qs.filter(priority='low').count()

    completed_count = team_tasks_qs.filter(status='completed').count()
    in_progress_count = team_tasks_qs.filter(status='in_progress').count()
    pending_count = team_tasks_qs.filter(status='pending').count()

    # 5. Get Users for the Report Dropdown 
    # Only showing users in the same department
    department_users = CustomUser.objects.filter(department=manager_dept).order_by('first_name')
    notifications = Notification.objects.filter(user=manager).order_by("-created_at")[:5]
    
    # Count how many are unread
    unread_count = Notification.objects.filter(user=manager, read=False).count()
    
    # 6. Apply Search & Filters from the HTML Form
    tasks = team_tasks_qs 
    
    # --- EXISTING FILTERS ---
    q = request.GET.get("q", "").strip()
    if q:
        tasks = tasks.filter(
            Q(title__icontains=q) | Q(assignee__first_name__icontains=q) | Q(assignee__email__icontains=q)
        )
    
    status_filter = request.GET.get("status")
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    priority_filter = request.GET.get("priority")
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)

    # --- NEW DEADLINE FILTER ---
    deadline_filter = request.GET.get("deadline_filter")
    today = timezone.now().date()

    if deadline_filter == "overdue":
        # Tasks where deadline has passed and are NOT completed
        tasks = tasks.filter(deadline__lt=today).exclude(status='completed')
    elif deadline_filter == "today":
        tasks = tasks.filter(deadline=today)
    elif deadline_filter == "this_week":
        next_week = today + timedelta(days=7)
        tasks = tasks.filter(deadline__range=[today, next_week])
    # elif deadline_filter == "no_deadline":
    #     tasks = tasks.filter(deadline__isnull=True)

    # Final ordering
    tasks = tasks.order_by("-created_at")

    # 7. Context to pass to HTML
    context = {
        "tasks": tasks,
        "team_tasks_count": team_tasks_qs.count(),
        "current_deadline_filter": deadline_filter, # Total for the top cards
        "notifications": notifications,
        "unread_notifications_count": unread_count,
        # Chart Data
        "high_priority_count": high_count,
        "medium_priority_count": medium_count,
        "low_priority_count": low_count,
        "completed_count": completed_count,
        "in_progress_count": in_progress_count,
        "pending_count": pending_count,
        
        # Dropdown Data
        "department_users": department_users,
    }
    
    return render(request, "manager_dashboard.html", context)

@login_required
def member_dashboard(request):
    if not (request.user.is_member or request.user.is_superuser):
        messages.error(request, "Unauthorized Access.")
        return redirect("home")

    base_qs = Task.objects.filter(assignee=request.user)
    today = timezone.localtime(timezone.now()).date()

    # --- NEW: FETCH NOTIFICATIONS ---
    user_notifications = request.user.notifications.all() # Uses related_name="notifications"
    unread_notifications_count = user_notifications.filter(read=False).count()
    # Get recent 5 for the dropdown/panel
    recent_notifications = user_notifications[:5]

    # 1. SUMMARY COUNTS (Calculated before filtering)
    pending_count = base_qs.exclude(status='completed').count()
    high_priority_count = base_qs.filter(priority='high').exclude(status='completed').count()
    completed_count = base_qs.filter(status='completed').count()
    overdue_count = base_qs.exclude(status='completed').filter(deadline__date__lt=today).count()
    # 2. FILTERING LOGIC
    tasks_qs = base_qs.exclude(status='completed')

    # Search query
    q = request.GET.get('q')
    if q:
        tasks_qs = tasks_qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    # Priority filter
    priority = request.GET.get('priority')
    if priority:
        tasks_qs = tasks_qs.filter(priority=priority)

    # Status filter
    status = request.GET.get('status')
    if status:
        tasks_qs = tasks_qs.filter(status=status)

    # Deadline filter
    deadline_filter = request.GET.get('deadline')
    if deadline_filter == 'overdue':
        tasks_qs = tasks_qs.filter(deadline__date__lt=today) 
    elif deadline_filter == 'today':
        tasks_qs = tasks_qs.filter(deadline__date=today)
    elif deadline_filter == 'week':
        tasks_qs = tasks_qs.filter(deadline__date__range=[today, today + timedelta(days=7)])

    # Order the active tasks
    tasks_qs = tasks_qs.order_by("priority", "deadline", "-created_at")

    # 3. HISTORY LOGIC (Crucial: Define the variable used in your template)
    completed_tasks = base_qs.filter(status='completed').order_by("-completed_at")

    # 4. CHART DATA PREPARATION
    bar_labels = [] 
    bar_data = []
    for i in range(5):
        target_date = today + timedelta(days=i)
        daily_count = base_qs.exclude(status='completed').filter(deadline__date=target_date).count()
        bar_labels.append(target_date.strftime("%a %d")) 
        bar_data.append(daily_count)  

    donut_pending = base_qs.filter(status='pending').count() 
    donut_progress = base_qs.filter(status='in_progress').count()
    donut_data = [donut_pending, donut_progress, completed_count]

    ctx = {
        "tasks": tasks_qs[:200], 
        "completed_tasks": completed_tasks, # This fixed the history area
        "overdue_count": overdue_count,
        "pending_count": pending_count,
        "high_priority_count": high_priority_count,
        "completed_count": completed_count,
        "bar_labels": bar_labels,
        "bar_data": bar_data,
        "donut_data": donut_data,
        "notifications": recent_notifications,
        "unread_notifications_count": unread_notifications_count,
    }
    return render(request, "member_dashboard.html", ctx)


@login_required
def start_task(request, pk):
    task = get_object_or_404(Task, pk=pk, assignee=request.user)
    
    if task.status == 'pending': # Assuming your model uses 'pending'
        task.status = 'in_progress' # Assuming your model uses 'in_progress'
        task.save()
        messages.success(request, f"Task '{task.title}' moved to In Progress.")
    
    return redirect('member_dashboard')
# -- Basic task actions used by templates / links ---------------------------------


@login_required 
def complete_task(request, pk):
    """Mark a task completed (POST expected)."""
    task = get_object_or_404(Task, pk=pk)
    # basic authorization: creator, assignee, managers or admins can mark
    if not (request.user.is_admin or request.user.is_manager or task.assignee == request.user or task.creator == request.user):
        messages.error(request, "You don't have permission to mark this task.")
        return redirect("dashboard")

    if request.method == "POST": 
        task.mark_completed()
        messages.success(request, f"Task '{task.title}' marked as completed.")
    return redirect(request.META.get("HTTP_REFERER", reverse("dashboard")))


@login_required
def delete_task(request, pk):
    """Delete a task (POST expected)."""
    task = get_object_or_404(Task, pk=pk)
    if not (request.user.is_admin or request.user.is_manager or task.creator == request.user):
        messages.error(request, "You don't have permission to delete this task.")
        return redirect("dashboard")

    if request.method == "POST":
        title = task.title
        task.delete()
        messages.success(request, f"Task '{title}' deleted.")
    # prefer referer so we return to the page where action was triggered
    return redirect(request.META.get("HTTP_REFERER", reverse("dashboard")))


# @login_required
# def update_task(request, pk):
#     """
#     Update task. 
#     GET -> Render update form with pre-filled data and filtered user list.
#     POST -> Update task details with security checks.
#     """
#     task = get_object_or_404(Task, pk=pk)
    
#     # 1. Authority Check
#     if not (request.user.is_admin or request.user.is_manager or task.creator == request.user or task.assignee == request.user):
#         messages.error(request, "You don't have permission to update this task.")
#         return redirect("dashboard")

#     # 2. FILTER USERS: Only get users from the Manager's department
#     # This list is needed for both rendering the dropdown (GET) and validating the input (POST)
#     department_users = CustomUser.objects.filter(
#         department=request.user.department
#     ).exclude(
#         id=request.user.id
#     ).order_by("first_name", "email")

#     if request.method == "POST":
#         title = request.POST.get("title", "").strip()
#         description = request.POST.get("description", "").strip()
#         assignee_id = request.POST.get("assignee")
#         priority = request.POST.get("priority", Task.PRIORITY_MEDIUM)
#         status = request.POST.get("status", task.status)
#         deadline = request.POST.get("deadline") or None

#         if title:
#             task.title = title
#         task.description = description
#         task.priority = priority
#         task.status = status

#         # Handle Deadline
#         if deadline:
#             try:
#                 dt = parse_datetime(deadline) or parse_date(deadline)
#                 if dt:
#                     if not isinstance(dt, _dt):
#                         dt = timezone.make_aware(_dt.combine(dt, _time.min), timezone.get_current_timezone())
#                     elif timezone.is_naive(dt):
#                         dt = timezone.make_aware(dt, timezone.get_current_timezone())
#                     task.deadline = dt
#             except Exception:
#                 pass
#         else:
#             task.deadline = None

#         # Handle Assignee
#         if assignee_id:
#             try:
#                 # 3. SECURITY CHECK: Ensure the assignee belongs to your department
#                 assignee = CustomUser.objects.get(
#                     pk=int(assignee_id), 
#                     department=request.user.department
#                 )
#                 task.assignee = assignee
#             except CustomUser.DoesNotExist:
#                 messages.error(request, "Invalid assignee or user is not in your department.")
#                 # We do not stop the save here, but we don't update the assignee. 
#                 # Alternatively, you could return render(...) with an error.
#             except Exception:
#                 task.assignee = None
#         else:
#             # If the dropdown was cleared (value=""), unassign the task
#             task.assignee = None
  
#         task.save()
#         messages.success(request, f"Task updated.") 
#         return redirect(request.META.get("HTTP_REFERER", reverse("manager_dashboard")))

#     # 4. GET Request - Render the Template
#     # We pass 'users' so the dropdown shows only your department members.
#     # You will need a template named 'update_task.html' (similar to create_newtask.html)
#     context = {
#         'task': task,
#         'users': department_users,
#     }
#     return render(request, "edit_task.html", context) 


# ---------------------------
# Simple create & edit views (render templates + handle POST)
# ---------------------------

@login_required
def create_task(request): 
    """
    Create new task. GET -> render form, POST -> create and redirect to manager dashboard.
    Template: create_newtask.html
    """
    # 1. Authority Check
    if not (request.user.is_manager or request.user.is_admin):
        messages.error(request, "Unauthorized Access.")
        return redirect("dashboard")

    # 2. FILTER USERS: Only get users from the Manager's department
    # We also exclude the manager themselves (optional) so they don't assign tasks to themselves
    users = CustomUser.objects.filter(
        department=request.user.department
    ).exclude(
        id=request.user.id 
    ).order_by("first_name", "email")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        priority = request.POST.get("priority", Task.PRIORITY_MEDIUM)
        status = request.POST.get("status", Task.STATUS_PENDING)
        deadline = request.POST.get("deadline") or None
        assignee_id = request.POST.get("assignee")

        if not title:
            messages.error(request, "Title is required.")
            return render(request, "create_newtask.html", {"users": users})

        assignee = None
        if assignee_id:
            try:
                # 3. SECURITY CHECK: Ensure the submitted assignee ID actually belongs to the department
                assignee = CustomUser.objects.get(
                    pk=int(assignee_id), 
                    department=request.user.department
                )
            except CustomUser.DoesNotExist:
                # If ID doesn't exist OR user is in a different department
                messages.error(request, "You cannot assign tasks to users outside your department.")
                assignee = None
            except Exception:
                assignee = None

        task = Task(
            title=title,
            description=description,
            creator=request.user,
            assignee=assignee,
            priority=priority,
            status=status,
        )

        # parse deadline if provided
        if deadline:
            try:
                dt = parse_datetime(deadline) or parse_date(deadline)
                if dt:
                    if not isinstance(dt, _dt):
                        dt = timezone.make_aware(_dt.combine(dt, _time.min), timezone.get_current_timezone())
                    elif timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone.get_current_timezone())
                    task.deadline = dt
            except Exception:
                pass

        task.save()
        messages.success(request, f"Task '{task.title}' created.")
        return redirect("manager_dashboard")

    # GET
    return render(request, "create_newtask.html", {"users": users})


@login_required
def edit_task(request, pk):
    """
    Render edit form (GET) and handle update (POST).
    Template: edit_task.html
    """
    task = get_object_or_404(Task, pk=pk)

    if not (request.user.is_admin or request.user.is_manager or task.creator == request.user or task.assignee == request.user):
        messages.error(request, "You don't have permission to edit this task.")
        return redirect("dashboard")

    department_users = CustomUser.objects.filter(
        department=request.user.department
    ).exclude(
        id=request.user.id
    ).order_by("first_name", "email")

    if request.method == "POST":
        # Reuse the same update logic as update_task (keeps behavior consistent)
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        assignee_id = request.POST.get("assignee")
        priority = request.POST.get("priority", Task.PRIORITY_MEDIUM)
        status = request.POST.get("status", task.status)
        deadline = request.POST.get("deadline") or None

        if title:
            task.title = title
        task.description = description
        task.priority = priority
        task.status = status

        if deadline:
            try:
                dt = parse_datetime(deadline) or parse_date(deadline)
                if dt:
                    if not isinstance(dt, _dt):
                        dt = timezone.make_aware(_dt.combine(dt, _time.min), timezone.get_current_timezone())
                    elif timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone.get_current_timezone())
                    task.deadline = dt
            except Exception:
                pass
        else:
            task.deadline = None 

        if assignee_id:
            try:
                assignee = CustomUser.objects.get(
                    pk=int(assignee_id),
                    department=request.user.department
                )
                task.assignee = assignee
            except CustomUser.DoesNotExist:
                messages.error(request, "Invalid assignee or user is not in your department.")
            except Exception:
                task.assignee = None

        else:
            task.assignee = None      
        task.save()
        messages.success(request, f"Task '{task.title}' updated.")
        return redirect("manager_dashboard")

    # GET -> render the edit page 
    ctx = {"task": task, "users": department_users}
    # ctx.update(_get_notification_context(request.user))
    return render(request, "edit_task.html", ctx)
