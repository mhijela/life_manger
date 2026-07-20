from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import User
from apps.core.mixins import paginate_queryset

from .forms import DailyTaskForm
from .models import DailyTask


@login_required
def list_view(request):
    queryset = DailyTask.objects.select_related(
        'assigned_to', 'subscriber', 'device', 'created_by'
    )
    selected_date = request.GET.get('date', '')
    status = request.GET.get('status', '')
    task_type = request.GET.get('type', '')
    assigned_to = request.GET.get('assigned_to', '')
    search = request.GET.get('q', '').strip()

    if selected_date:
        queryset = queryset.filter(scheduled_date=selected_date)
    if status:
        queryset = queryset.filter(status=status)
    if task_type:
        queryset = queryset.filter(task_type=task_type)
    if assigned_to:
        queryset = queryset.filter(assigned_to_id=assigned_to)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(location__icontains=search)
            | Q(subscriber__full_name__icontains=search)
            | Q(subscriber__phone__icontains=search)
        )

    return render(request, 'daily_tasks/list.html', {
        'page_obj': paginate_queryset(request, queryset),
        'status_choices': DailyTask.STATUS_CHOICES,
        'type_choices': DailyTask.TYPE_CHOICES,
        'users': User.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'email'
        ),
        'selected_date': selected_date,
        'current_status': status,
        'current_type': task_type,
        'current_assigned_to': assigned_to,
        'search': search,
        'today': timezone.localdate(),
    })


@login_required
def create_view(request):
    if request.method == 'POST':
        form = DailyTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            messages.success(request, 'تمت إضافة المهمة بنجاح.')
            return redirect('daily_tasks:list')
    else:
        form = DailyTaskForm(initial={
            'scheduled_date': request.GET.get('date') or timezone.localdate(),
            'assigned_to': request.user,
        })
    return render(request, 'daily_tasks/form.html', {
        'form': form,
        'title': 'إضافة مهمة',
    })


@login_required
def edit_view(request, pk):
    task = get_object_or_404(DailyTask, pk=pk)
    if request.method == 'POST':
        form = DailyTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث المهمة.')
            return redirect('daily_tasks:list')
    else:
        form = DailyTaskForm(instance=task)
    return render(request, 'daily_tasks/form.html', {
        'form': form,
        'title': 'تعديل المهمة',
        'task': task,
    })


@login_required
def complete_view(request, pk):
    task = get_object_or_404(DailyTask, pk=pk)
    if request.method == 'POST':
        task.status = 'completed'
        task.save()
        messages.success(request, 'تم تحديد المهمة كمكتملة.')
    return redirect('daily_tasks:list')


@login_required
def delete_view(request, pk):
    task = get_object_or_404(DailyTask, pk=pk)
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'تم حذف المهمة.')
        return redirect('daily_tasks:list')
    return render(request, 'daily_tasks/delete.html', {'task': task})
