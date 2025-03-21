from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# User roles

class Profile(models.Model):
    class Role(models.TextChoices):
        PROJECT_MANAGER = 'Project Manager', 'Project Manager'
        DEVELOPER = 'Developer', 'Developer'

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    

class Task(models.Model):
    STATUS_CHOICES = [
        ('Not Started', 'Not Started'),
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Review', 'Review'),  # New status
        ('Submitted', 'Submitted'),
        ('Completed', 'Completed'),
    ]

    PRIORITY_MAPPING = {
        'Urgent': 1,
        'High': 2,
        'Medium': 3,
        'Low': 4,
    }

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ManyToManyField(User, related_name='tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Started')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    due_date = models.DateField()
    project_link = models.URLField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True, null=True)


    def __str__(self):
        return f"{self.title} - {self.priority}"
    
    class Meta:
        ordering = ['priority']

    def priority_order(self):
        return self.PRIORITY_MAPPING[self.priority]
    

class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.title}"


class RecentActivity(models.Model):
    ACTION_CHOICES = [
        ('created', 'created a task'),
        ('updated', 'updated a task'),
        ('commented', 'commented on a task'),
        ('completed', 'marked a task as completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Who performed the action
    task = models.ForeignKey('Task', on_delete=models.CASCADE)  # The task related to the action
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)  # Action performed
    timestamp = models.DateTimeField(auto_now_add=True)  # When it happened

    class Meta:
        ordering = ['-timestamp']  # Show latest first

    def __str__(self):
        return f"{self.user.username} {self.get_action_display()} on {self.task.title}"

