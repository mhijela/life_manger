from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from apps.core.mixins import paginate_queryset
from apps.subscribers.models import Subscriber
from apps.settings_app.models import SystemSettings
from .models import MessageTemplate, MessageLog
from .forms import SendMessageForm, BulkMessageForm, MessageTemplateForm
from .services.sms_service import SMSService


@login_required
def index(request):
    page_obj = paginate_queryset(request, MessageLog.objects.select_related('template'))
    templates = MessageTemplate.objects.filter(is_active=True)
    sms = SMSService()
    sms_balance = sms.check_balance() if sms.is_configured() else None
    return render(request, 'messages/index.html', {
        'page_obj': page_obj,
        'templates': templates,
        'sms_balance': sms_balance,
        'sms_configured': sms.is_configured(),
    })


@login_required
def send_view(request):
    if request.method == 'POST':
        form = SendMessageForm(request.POST)
        if form.is_valid():
            sms = SMSService()
            log = sms.send(
                form.cleaned_data['recipient'],
                form.cleaned_data['message'],
                template=form.cleaned_data.get('selected_template'),
            )
            if log.status == 'sent':
                django_messages.success(request, 'تم إرسال الرسالة بنجاح.')
            else:
                django_messages.error(request, log.error_message or 'فشل إرسال الرسالة.')
            return redirect('messages:index')
    else:
        form = SendMessageForm()
    return render(request, 'messages/send.html', {'form': form, 'title': 'إرسال رسالة'})


@login_required
def bulk_send(request):
    if request.method == 'POST':
        form = BulkMessageForm(request.POST)
        if form.is_valid():
            template = form.cleaned_data['template']
            status = form.cleaned_data.get('status')
            subscribers = Subscriber.objects.all()
            if status:
                subscribers = subscribers.filter(status=status)
            settings = SystemSettings.load()
            sms = SMSService()
            count = 0
            for sub in subscribers:
                context = {
                    'name': sub.full_name,
                    'phone': sub.phone,
                    'company': settings.company_name,
                    'amount': sub.monthly_price,
                }
                sub_obj = sub.active_subscription
                if sub_obj:
                    context['expiry_date'] = sub_obj.end_date
                sms.send_template(sub.phone, template, context)
                count += 1
            django_messages.success(request, f'تم إرسال {count} رسالة.')
            return redirect('messages:index')
    else:
        form = BulkMessageForm()
    return render(request, 'messages/bulk.html', {'form': form, 'title': 'إرسال جماعي'})


@login_required
def template_list(request):
    templates = MessageTemplate.objects.all()
    return render(request, 'messages/templates.html', {'templates': templates})


@login_required
def template_create(request):
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            django_messages.success(request, 'تم إضافة القالب.')
            return redirect('messages:templates')
    else:
        form = MessageTemplateForm()
    return render(request, 'messages/template_form.html', {'form': form, 'title': 'إضافة قالب'})


@login_required
def template_edit(request, pk):
    template = get_object_or_404(MessageTemplate, pk=pk)
    if request.method == 'POST':
        form = MessageTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            django_messages.success(request, 'تم تحديث القالب.')
            return redirect('messages:templates')
    else:
        form = MessageTemplateForm(instance=template)
    return render(request, 'messages/template_form.html', {
        'form': form,
        'title': 'تعديل قالب',
        'template': template,
    })


@login_required
def template_delete(request, pk):
    if request.method != 'POST':
        return redirect('messages:templates')

    template = get_object_or_404(MessageTemplate, pk=pk)
    name = template.name
    template.delete()
    django_messages.success(request, f'تم حذف القالب «{name}».')
    return redirect('messages:templates')
