from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, logout, authenticate
from django.core.paginator import Paginator
from .forms import CommentForm, RegisterForm, TaskForm, TaskUpdateForm
from .decorators import role_required
from django.contrib import messages
from datetime import date
from collections import Counter
from django.db.models import Count
from django.db.models import Q, Case, When, Value, IntegerField
from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from django.contrib.auth.decorators import login_required
from .models import RecentActivity, Task

# Create your views here.


def registerView(request):
    if request.user.is_authenticated:
        return redirect('task_list')  # Redirect if already logged in

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")  # Success message
            return redirect('task_list')
        else:
            messages.error(request, "Registration failed. Please check your details.")

    else:
        form = RegisterForm()

    return render(request, 'auth/register.html', {'form': form})



def loginView(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")  # Show welcome message
            return redirect('task_list')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    
    return render(request, 'auth/login.html')

def logoutView(request):
    messages.success(request, "You have been logged out.")  # Ensure message appears
    logout(request)

    # Redirect to login page to avoid message persistence
    return redirect('login')


def send_task_email(task, subject, template_name, recipients):
    """Send task-related email notifications with both HTML and plain text versions."""
    if not recipients:  # Prevent errors if no recipients
        return

    context = {
        'task': task,
        'task_url': f"http://127.0.0.1:8000/task/{task.id}"
    }

    # ✅ Corrected line - Use `template_name` properly
    html_message = render_to_string(f'emails/{template_name}', context)
    plain_message = strip_tags(html_message)  # Convert HTML to plain text

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        html_message=html_message,
    )

def send_task_update_email(task, updated_by, old_status):
    """Send email notifications when a task is updated."""
    recipients = [user.email for user in task.assigned_to.all()] + [task.created_by.email]
    if not recipients:
        return  # Avoid sending if no recipients

    context = {
        'task': task,
        'updated_by': str(updated_by),
        'old_status': old_status,
        'new_status': task.status,  # Updated status
        'task_url': f"http://127.0.0.1:8000/task/{task.id}"
    }

    html_message = render_to_string('emails/task_updated_email.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject=f"Task Updated: {task.title}",
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        html_message=html_message,
    )



@login_required
@role_required(['Project Manager'])
def createTask(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)  # Don't save yet
            task.created_by = request.user  # Assign the logged-in user
            task.save()  # Now save
            form.save_m2m()  # Save ManyToMany relationships

            # Log the activity
            log_activity(request.user, task, "created")

            # 📩 Send email to assigned developers
            recipients = [user.email for user in task.assigned_to.all()]
            if recipients:
                send_task_email(task, "New Task Assigned", "task_assigned_email.html", recipients)

            messages.success(request, "Task created successfully!")
            return redirect('task_list')
        else:
            messages.error(request, "Task creation failed. Please check the form.")
    else:
        form = TaskForm()

    context = {'form': form}
    return render(request, 'tasks/create_task.html', context)


@login_required
@role_required(['Project Manager', 'Developer'])
def updateTaskStatus(request, id):
    task = get_object_or_404(Task, id=id)

    # Ensure only assigned Developers or the creator (Project Manager) can update
    if request.user != task.created_by and request.user not in task.assigned_to.all():
        return HttpResponseForbidden("You do not have permission to edit this task.")

    # Define allowed status updates
    if request.user.profile.role == 'Developer':
        allowed_statuses = ['In Progress', 'Submitted']
    else:
        allowed_statuses = [choice[0] for choice in Task.STATUS_CHOICES]

    if request.method == 'POST':
        status = request.POST.get('status')
        project_link = request.POST.get('project_link', '')

        # Validate status update
        if status not in allowed_statuses:
            messages.error(request, "You are not allowed to set this status.")
        else:
            old_status = task.status  # Store the old status before updating
            task.status = status
            
            if request.user.profile.role == 'Developer':
                task.project_link = project_link  # Update project link

            task.save()  # Save updated task

            # Log the activity
            log_activity(request.user, task, "updated")

            # Send Email Notification
            recipients = [user.email for user in task.assigned_to.all()] + [task.created_by.email]
            send_task_update_email(task, updated_by=request.user, old_status=old_status)

            messages.success(request, "Task updated successfully.")
            return redirect('task_list')

    context = {
        'task': task,
        'allowed_statuses': allowed_statuses
    }
    return render(request, 'tasks/update_task.html', context)


def taskList(request):
    tasks = Task.objects.all()

    # ✅ Get filters from request
    query = request.GET.get('q', '')  
    status_filter = request.GET.get('status', '')  
    priority_filter = request.GET.get('priority', '')  
    start_date = request.GET.get('start_date', '')  
    end_date = request.GET.get('end_date', '')  

    # ✅ Apply search filter (Title or Description)
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))

    # ✅ Filter by Status
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    # ✅ Filter by Priority
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)

    # ✅ Filter by Due Date Range
    if start_date:
        tasks = tasks.filter(due_date__gte=start_date)
    if end_date:
        tasks = tasks.filter(due_date__lte=end_date)

    # ✅ Sorting: Completed tasks last, then by priority
    priority_order = Case(
        When(priority="Urgent", then=Value(1)),
        When(priority="High", then=Value(2)),
        When(priority="Medium", then=Value(3)),
        When(priority="Low", then=Value(4)),
        default=Value(5),
        output_field=IntegerField(),
    )

    status_order = Case(
        When(status="Completed", then=Value(2)),  # Completed tasks last
        default=Value(1),  # Other statuses first
        output_field=IntegerField(),
    )

    tasks = tasks.annotate(
        priority_value=priority_order,
        status_value=status_order
    ).order_by("status_value", "priority_value", "-created_at")

    # ✅ Pagination: Show 8 tasks per page
    paginator = Paginator(tasks, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ Pass choices for dropdown filters
    context = {
        'page_obj': page_obj,
        'query': query,
        'status_choices': Task.STATUS_CHOICES,  
        'priority_choices': Task.PRIORITY_CHOICES,
    }

    return render(request, 'tasks/task_list.html', context)


@login_required
def taskDetail(request, id):
    task = get_object_or_404(Task, id=id)
    comments = task.comments.all()
    form = CommentForm()

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.task = task
            comment.save()

            # Log the activity
            log_activity(request.user, task, "commented")


            return redirect('task_detail', id=task.id)  # Refresh the page
        else:
            print(form.errors)  # Debugging: This will show errors in the terminal

    context = {
        'task': task,
        'comments': comments,
        'form': form
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def dashboard(request):
    tasks = Task.objects.all()

    # Count tasks by status
    status_counter = Counter(task.status for task in tasks)
    status_labels = list(status_counter.keys())
    status_counts = list(status_counter.values())

    # Key Metrics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status="Completed").count()
    overdue_tasks = tasks.filter(due_date__lt=date.today()).exclude(status="Completed").count()

    # Count tasks by priority
    priority_data = Task.objects.values('priority').annotate(count=Count('priority'))
    priority_labels = [item['priority'] for item in priority_data]
    priority_counts = [item['count'] for item in priority_data]

    recent_activities = RecentActivity.objects.all()[:10]  # Get latest 10 activities

    # ✅ Merge all data into a single context dictionary
    context = {
        'status_labels': status_labels,
        'status_counts': status_counts,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'priority_labels': priority_labels,
        'priority_counts': priority_counts,
        'recent_activities': recent_activities
    }

    return render(request, 'tasks/dashboard.html', context)


def log_activity(user, task, action):
    activity = RecentActivity.objects.create(user=user, task=task, action=action)

    # Send WebSocket message
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "recent_activity",
        {
            "type": "send_activity",
            "message": f"{user.username} {activity.get_action_display()} on {task.title}"
        }
    )
