from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from apps.core.mixins import paginate_queryset
from .models import Device
from .forms import DeviceForm, MaintenanceNoteForm


@login_required
def list_view(request):
    queryset = Device.objects.select_related('subscriber')
    search = request.GET.get('q', '')
    device_type = request.GET.get('type')
    if search:
        queryset = queryset.filter(models.Q(name__icontains=search) | models.Q(ip_address__icontains=search))
    if device_type:
        queryset = queryset.filter(device_type=device_type)
    page_obj = paginate_queryset(request, queryset)
    return render(request, 'devices/list.html', {
        'page_obj': page_obj, 'search': search,
        'type_choices': Device.TYPE_CHOICES, 'current_type': device_type,
    })


@login_required
def create_view(request):
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الجهاز.')
            return redirect('devices:list')
    else:
        form = DeviceForm()
    return render(request, 'devices/form.html', {'form': form, 'title': 'إضافة جهاز'})


@login_required
def edit_view(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الجهاز.')
            return redirect('devices:list')
    else:
        form = DeviceForm(instance=device)
    return render(request, 'devices/form.html', {'form': form, 'title': 'تعديل جهاز'})


@login_required
def delete_view(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.delete()
        messages.success(request, 'تم حذف الجهاز.')
        return redirect('devices:list')
    return render(request, 'devices/delete.html', {'device': device})


@login_required
def detail_view(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        note_form = MaintenanceNoteForm(request.POST)
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.device = device
            note.created_by = request.user
            note.save()
            messages.success(request, 'تم إضافة ملاحظة الصيانة.')
            return redirect('devices:detail', pk=pk)
    else:
        note_form = MaintenanceNoteForm()
    return render(request, 'devices/detail.html', {
        'device': device,
        'notes': device.maintenance_notes.all(),
        'note_form': note_form,
    })
