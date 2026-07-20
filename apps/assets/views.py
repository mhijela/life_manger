from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.core.mixins import paginate_queryset
from .models import Asset, AssetHistory
from .forms import AssetForm


@login_required
def list_view(request):
    page_obj = paginate_queryset(request, Asset.objects.select_related('category', 'assigned_to'))
    return render(request, 'assets/list.html', {'page_obj': page_obj})


@login_required
def create_view(request):
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save()
            if asset.assigned_to:
                asset.status = 'assigned'
                asset.save()
                AssetHistory.objects.create(asset=asset, action='assigned', subscriber=asset.assigned_to)
            messages.success(request, 'تم إضافة الأصل.')
            return redirect('assets:list')
    else:
        form = AssetForm()
    return render(request, 'assets/form.html', {'form': form, 'title': 'إضافة أصل'})


@login_required
def edit_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الأصل.')
            return redirect('assets:list')
    else:
        form = AssetForm(instance=asset)
    return render(request, 'assets/form.html', {'form': form, 'title': 'تعديل أصل'})


@login_required
def return_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        subscriber = asset.assigned_to
        asset.assigned_to = None
        asset.return_date = timezone.now().date()
        asset.status = 'returned'
        asset.save()
        AssetHistory.objects.create(asset=asset, action='returned', subscriber=subscriber)
        messages.success(request, 'تم إرجاع الأصل.')
    return redirect('assets:list')


@login_required
def detail_view(request, pk):
    asset = get_object_or_404(Asset.objects.select_related('category', 'assigned_to'), pk=pk)
    return render(request, 'assets/detail.html', {
        'asset': asset,
        'history': asset.history.select_related('subscriber'),
    })
