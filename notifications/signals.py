from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from django.utils.timezone import localtime
from .models import Notification
from tasks.models import Task
from users.models import CustomUser


def _display_name(user):
    """Helper to get a readable name for the email greeting."""
    if not user: return ""
    return (getattr(user, "full_name", "") or 
            (user.get_full_name() if hasattr(user, 'get_full_name') else "") or 
            user.email or 
            user.username)

def _format_date(dt):
    """Helper to format date consistently and fix the 'one day off' timezone issue."""
    if not dt: return "None"
    # localtime() converts the UTC database time to your project's TIME_ZONE
    return localtime(dt).strftime('%A, %B %d, %Y')

@receiver(post_save, sender=CustomUser)
def notify_admins_of_new_registration(sender, instance, created, **kwargs):
    """
    Triggers when a new CustomUser is created. 
    Sends an in-app notification to all Admins/Superusers.
    No email is sent.
    """
    if created:
        # 1. Prepare the notification message
        full_name = f"{instance.first_name} {instance.last_name}".strip()
        user_identifier = full_name if full_name else instance.email
        message = f"New user registered: {user_identifier}."

        # 2. Find all recipients (Admins by role OR Superusers)
        admins = CustomUser.objects.filter(
            Q(role=CustomUser.ROLE_ADMIN) | Q(is_superuser=True)
        ).distinct()

        # 3. Create notifications (In-app only)
        for admin in admins:
            # We set task=None because registration isn't linked to a specific task
            Notification.objects.create(
                user=admin, 
                task=None, 
                message=message
            )

@receiver(pre_save, sender=Task)
def capture_old_task_values(sender, instance, **kwargs):
    """ 
    Captures values BEFORE the save happens so we can compare 
    them to the new values in post_save.
    """
    if instance.pk:
        try:
            old_task = Task.objects.get(pk=instance.pk)
            instance._old_title = old_task.title
            instance._old_priority = old_task.priority
            instance._old_deadline = old_task.deadline
            instance._old_description = old_task.description
            instance._old_status = old_task.status
        except Task.DoesNotExist:
            pass

@receiver(post_save, sender=Task)
def notify_on_task_save(sender, instance, created, **kwargs):
    """
    Sends notifications and emails based on creation or specific updates.
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Task Manager <sameesheikh02@gmail.com>")
    assignee = instance.assignee
    creator = instance.creator
    
    # Common variables for formatting
    priority_label = instance.get_priority_display()
    current_deadline_str = _format_date(instance.deadline)

    # --- CASE 1: NEW TASK ASSIGNED ---
    if created and assignee:
        subject = f"New Task Assigned: {instance.title}"
        msg = f"You've been assigned a new task: '{instance.title}'."
        
        email_body = (
            f"Hi {_display_name(assignee)},\n\n"
            f"{msg}\n\n"
            f"DETAILS:\n"
            f"- Priority: {priority_label}\n"
            f"- Deadline: {current_deadline_str}\n\n"
            f"Please log in to your dashboard to view the full details."
        )
        
        Notification.objects.create(user=assignee, task=instance, message=msg)
        if assignee.email:
            send_mail(subject, email_body, from_email, [assignee.email], fail_silently=False)
        return 
    #  STATUS CHANGE LOGIC
    if not created and hasattr(instance, '_old_status') and instance._old_status != instance.status:
        
        # Transition A: Pending -> In Progress (Notification ONLY)
        if instance._old_status == 'pending' and instance.status == 'in_progress':
            msg = f"Task '{instance.title}' is now In Progress (started by {assignee.first_name if assignee else 'member'} {assignee.last_name if assignee else ''})."
            Notification.objects.create(user=creator, task=instance, message=msg)
            # No email sent here as requested

        # Transition B: In Progress -> Completed (Notification AND Email) 
        elif instance.status == 'completed':
            subject = f"Task Completed: {instance.title}"
            msg = f"Task '{instance.title}' has been marked as Completed by {assignee.first_name if assignee else 'member'} {assignee.last_name if assignee else ''}."
            
            # 1. In-app Notification
            Notification.objects.create(user=creator, task=instance, message=msg)
            
            # 2. Email Notification
            if creator and creator.email:
                email_body = f"Hi {_display_name(creator)},\n\n{msg}"
                send_mail(subject, email_body, from_email, [creator.email], fail_silently=False)
    
    # --- CASE 2: TASK UPDATED (TITLE, PRIORITY, DEADLINE) ---
    if not created and assignee:
        changes = []
        
        # Check Title Change
        if hasattr(instance, '_old_title') and instance._old_title != instance.title:
            changes.append(f"Title changed from '{instance._old_title}' to '{instance.title}'")
        
        # Check Priority Change
        if hasattr(instance, '_old_priority') and instance._old_priority != instance.priority:
            # Convert internal code (e.g. 'high') to label ('High')
            old_p_label = dict(Task.PRIORITY_CHOICES).get(instance._old_priority, instance._old_priority)
            changes.append(f"Priority changed from {old_p_label} to {priority_label}")
            
        # Check Deadline Change
        if hasattr(instance, '_old_deadline') and instance._old_deadline != instance.deadline:
            old_dt_str = _format_date(instance._old_deadline)
            changes.append(f"Deadline changed from {old_dt_str} to\n {current_deadline_str}")

        if hasattr(instance, '_old_description') and instance._old_description != instance.description:
            changes.append("The task description has been updated.")

        if changes:
            subject = f"Task Updated: {instance.title}"
            change_summary = "\n- ".join(changes)
            email_body = (
                f"Hi {_display_name(assignee)},\n\n"
                f"The task '{instance.title}' has been updated with the following changes:\n\n"
                f"- {change_summary}\n\n"
                f"Log in to your dashboard to view the full details."
            ) 

            # Create in-app notification with a summary of changes
            notif_msg = f"Task '{instance.title}' updated: {', '.join(changes)}"
            Notification.objects.create(user=assignee, task=instance, message=notif_msg[:255])
            
            if assignee.email:
                send_mail(subject, email_body, from_email, [assignee.email], fail_silently=False)

    # --- CASE 3: TASK COMPLETED (NOTIFY CREATOR) ---
    # Using Task.STATUS_COMPLETED to avoid hardcoding strings
    # if instance.status == Task.STATUS_COMPLETED and instance.creator:
    #     subject = f"Task Completed: {instance.title}"
    #     msg = f"Task '{instance.title}' was marked completed by {assignee if assignee else 'someone'}."
        
    #     Notification.objects.create(user=instance.creator, task=instance, message=msg)
    #     if instance.creator.email:  
    #         send_mail(subject, f"Hi {_display_name(instance.creator)},\n\n{msg}", from_email, [instance.creator.email], fail_silently=False)


@receiver(post_delete, sender=Task)
def notify_on_task_delete(sender, instance, **kwargs):
    """
    Notify the assignee when a task is deleted.
    """
    if instance.assignee:
        msg = f"Task Deleted: The task '{instance.title}' has been removed by the manager."
        # Note: We don't link the task here because it's already being deleted from the DB
        Notification.objects.create(
            user=instance.assignee, 
            message=msg
        )