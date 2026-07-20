from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from apps.subscribers.models import Subscriber
from apps.finance.models import Payment, Expense, Debt, Cashbox
from apps.inventory.models import InventoryItem
from apps.assets.models import Asset
from apps.devices.models import Device
from apps.messages.models import MessageLog
from .exporters import export_to_excel, export_to_pdf


REPORT_TYPES = {
    'subscribers': 'تقرير المشتركين',
    'active_subscribers': 'المشتركون النشطون',
    'expired_subscribers': 'المشتركون المنتهون',
    'debts': 'تقرير الديون',
    'income': 'تقرير الدخل',
    'expenses': 'تقرير المصروفات',
    'profit_loss': 'تقرير الأرباح والخسائر',
    'inventory': 'تقرير المخزون',
    'assets': 'تقرير الأصول',
    'devices': 'تقرير الأجهزة',
    'messages': 'تقرير الرسائل',
}


def _get_date_filters(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('q', '')
    return date_from, date_to, search


def _get_subscriber_data(status=None, search=''):
    qs = Subscriber.objects.select_related('area')
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(Q(full_name__icontains=search) | Q(phone__icontains=search))
    headers = ['الاسم', 'الهاتف', 'المنطقة', 'الحالة', 'السعر الشهري']
    rows = [(s.full_name, s.phone, str(s.area or ''), s.get_status_display(), s.monthly_price) for s in qs]
    return headers, rows, qs


@login_required
def index(request):
    return render(request, 'reports/index.html', {'report_types': REPORT_TYPES})


@login_required
def report_view(request, report_type):
    if report_type not in REPORT_TYPES:
        return render(request, 'reports/index.html', {'report_types': REPORT_TYPES})

    date_from, date_to, search = _get_date_filters(request)
    export = request.GET.get('export')
    title = REPORT_TYPES[report_type]
    headers, rows, queryset = [], [], []

    if report_type == 'subscribers':
        headers, rows, queryset = _get_subscriber_data(search=search)
    elif report_type == 'active_subscribers':
        headers, rows, queryset = _get_subscriber_data(status='active', search=search)
    elif report_type == 'expired_subscribers':
        headers, rows, queryset = _get_subscriber_data(status='expired', search=search)
    elif report_type == 'debts':
        qs = Debt.objects.select_related('subscriber')
        if search:
            qs = qs.filter(subscriber__full_name__icontains=search)
        headers = ['المشترك', 'الإجمالي', 'المدفوع', 'المتبقي', 'الاستحقاق', 'الحالة']
        rows = [(d.subscriber.full_name, d.total_amount, d.paid_amount, d.remaining_amount, d.due_date, d.get_status_display()) for d in qs]
        queryset = qs
    elif report_type == 'income':
        qs = Payment.objects.select_related('subscriber', 'method')
        if date_from:
            qs = qs.filter(payment_date__gte=date_from)
        if date_to:
            qs = qs.filter(payment_date__lte=date_to)
        headers = ['المشترك', 'المبلغ', 'التاريخ', 'الطريقة']
        rows = [(p.subscriber.full_name if p.subscriber else '-', p.amount, p.payment_date, p.method.name) for p in qs]
        queryset = qs
    elif report_type == 'expenses':
        qs = Expense.objects.select_related('category')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        headers = ['العنوان', 'المبلغ', 'التاريخ', 'الفئة']
        rows = [(e.title, e.amount, e.date, e.category.name) for e in qs]
        queryset = qs
    elif report_type == 'profit_loss':
        headers = ['البند', 'المبلغ']
        rows = [
            ('إجمالي الدخل', Cashbox.total_income()),
            ('إجمالي المصروفات', Cashbox.total_expenses()),
            ('صافي الربح', Cashbox.balance()),
        ]
    elif report_type == 'inventory':
        qs = InventoryItem.objects.select_related('unit')
        headers = ['الصنف', 'الفئة', 'الكمية', 'الوحدة', 'الحد الأدنى']
        rows = [(i.name, i.category, i.quantity, i.unit.name, i.min_stock) for i in qs]
        queryset = qs
    elif report_type == 'assets':
        qs = Asset.objects.select_related('category', 'assigned_to')
        headers = ['الاسم', 'التسلسلي', 'الفئة', 'مُسلّم إلى', 'الحالة']
        rows = [(a.name, a.serial_number, a.category.name, str(a.assigned_to or ''), a.get_status_display()) for a in qs]
        queryset = qs
    elif report_type == 'devices':
        qs = Device.objects.all()
        headers = ['الاسم', 'النوع', 'IP', 'الموقع', 'الحالة']
        rows = [(d.name, d.get_device_type_display(), d.ip_address or '', d.location, d.get_status_display()) for d in qs]
        queryset = qs
    elif report_type == 'messages':
        qs = MessageLog.objects.all()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        headers = ['المستلم', 'الحالة', 'التاريخ']
        rows = [(m.recipient, m.get_status_display(), m.created_at.strftime('%Y-%m-%d %H:%M')) for m in qs]
        queryset = qs

    if export == 'excel':
        return export_to_excel(headers, rows, filename=report_type)
    if export == 'pdf':
        return export_to_pdf('reports/print.html', {
            'title': title, 'headers': headers, 'rows': rows,
            'date_from': date_from, 'date_to': date_to,
        }, filename=report_type)

    return render(request, 'reports/report.html', {
        'title': title,
        'report_type': report_type,
        'headers': headers,
        'rows': rows,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    })
