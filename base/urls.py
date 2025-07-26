from django.urls import path
from .views import create_superuser_once, dashboard, registerView, loginView, logoutView, taskDetail, taskList, createTask, updateTaskStatus

urlpatterns = [
    path('tasks', taskList, name='task_list'),
    path('register/', registerView, name='register'),
    path('login/', loginView, name='login'),
    path('logout/', logoutView, name='logout'),
    path('create/', createTask, name='create_task'),
    path('update<int:id>/', updateTaskStatus, name='update_task'),
    path('task/<int:id>/', taskDetail, name='task_detail'),
    path('', dashboard, name='dashboard'),
    # path('create-superuser/', create_superuser_once, name='create_superuser'),
]