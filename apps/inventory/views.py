from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from apps.core.mixins import paginate_queryset
from .models import InventoryItem, StockMovement
from .forms import InventoryItemForm, StockMovementForm


@login_required
def list_view(request):
    queryset = InventoryItem.objects.select_related('unit')
    search = request.GET.get('q', '')
    if search:
        queryset = queryset.filter(models.Q(name__icontains=search) | models.Q(category__icontains=search))
    page_obj = paginate_queryset(request, queryset)
    return render(request, 'inventory/list.html', {'page_obj': page_obj, 'search': search})


@login_required
def create_view(request):
    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الصنف.')
            return redirect('inventory:list')
    else:
        form = InventoryItemForm()
    return render(request, 'inventory/form.html', {'form': form, 'title': 'إضافة صنف'})


@login_required
def edit_view(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الصنف.')
            return redirect('inventory:list')
    else:
        form = InventoryItemForm(instance=item)
    return render(request, 'inventory/form.html', {'form': form, 'title': 'تعديل صنف'})


@login_required
def delete_view(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'تم حذف الصنف.')
        return redirect('inventory:list')
    return render(request, 'inventory/delete.html', {'item': item})


@login_required
def movement_create(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.created_by = request.user
            movement.save()
            movement.apply()
            messages.success(request, 'تم تسجيل حركة المخزون.')
            return redirect('inventory:list')
    else:
        form = StockMovementForm()
    return render(request, 'inventory/movement_form.html', {'form': form, 'title': 'حركة مخزون'})
