from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ContactForm


SITE = {
    'brand_ar': 'زيد تك',
    'brand_en': 'Zaid Tech',
    'tagline': 'للخدمات الرقمية وتكنولوجيا المعلومات',
    'phone': '+972592092020',
    'phone_display': '0592 092 020',
    'whatsapp': '972592092020',
    'email': 'info@zaidtech.ps',
    'address': 'فلسطين',
    'hours': 'الأحد – الخميس · 9:00 ص – 5:00 م',
    'show_social': False,
    'facebook': '',
    'instagram': '',
    'linkedin': '',
}


SERVICES = [
    {
        'icon': 'bi-window-sidebar',
        'title': 'تصميم وتطوير المواقع',
        'desc': 'مواقع سريعة، متجاوبة، بهوية بصرية قوية تحوّل الزوار إلى عملاء.',
    },
    {
        'icon': 'bi-cpu',
        'title': 'الأنظمة والبرامج المخصصة',
        'desc': 'حلول برمجية مبنية على احتياج عملك بدل القوالب الجاهزة.',
    },
    {
        'icon': 'bi-router',
        'title': 'تركيب وإدارة الشبكات',
        'desc': 'شبكات مستقرة وآمنة للأفراد والشركات مع إعداد ومتابعة احترافية.',
    },
    {
        'icon': 'bi-cloud-check',
        'title': 'الخوادم والحوسبة السحابية',
        'desc': 'بنية تحتية مرنة وقابلة للتوسع مع مراقبة واستمرارية تشغيل.',
    },
    {
        'icon': 'bi-tools',
        'title': 'الدعم الفني والصيانة',
        'desc': 'صيانة أجهزة الحاسوب وحل الأعطال بسرعة لتقليل توقف العمل.',
    },
    {
        'icon': 'bi-shield-lock',
        'title': 'الأمن السيبراني',
        'desc': 'حماية البيانات والأنظمة من التهديدات مع سياسات أمان عملية.',
    },
    {
        'icon': 'bi-graph-up-arrow',
        'title': 'التسويق الرقمي',
        'desc': 'إدارة محتوى وحملات رقمية تبني حضورك وتزيد وصولك للعملاء.',
    },
    {
        'icon': 'bi-lightbulb',
        'title': 'الاستشارات والتحول الرقمي',
        'desc': 'خارطة طريق تقنية واضحة من التقييم إلى التنفيذ والمتابعة.',
    },
]


WHY_US = [
    {'icon': 'bi-sliders', 'title': 'حلول حسب احتياجك', 'desc': 'نصمّم الحل على مقاس عملك لا العكس.'},
    {'icon': 'bi-award', 'title': 'جودة واحترافية', 'desc': 'تنفيذ مرتب بمعايير واضحة من البداية للنهاية.'},
    {'icon': 'bi-lightning-charge', 'title': 'تقنيات قابلة للتطوير', 'desc': 'أساس حديث ينمو مع توسّع مشروعك.'},
    {'icon': 'bi-cash-coin', 'title': 'أسعار واضحة', 'desc': 'عرض مناسب وشفاف بدون مفاجآت.'},
    {'icon': 'bi-safe2', 'title': 'أمان البيانات', 'desc': 'حماية وممارسات أمان مدمجة في كل حل.'},
    {'icon': 'bi-headset', 'title': 'دعم بعد التسليم', 'desc': 'متابعة وصيانة مستمرة بعد الإطلاق.'},
]


PROJECTS = [
    {
        'title': 'منصة خدمات رقمية',
        'category': 'مواقع إلكترونية',
        'tone': 'cyan',
        'desc': 'واجهة حديثة لعرض الخدمات وتحويل الزوار إلى طلبات.',
    },
    {
        'title': 'نظام إدارة عمليات',
        'category': 'أنظمة إدارة',
        'tone': 'violet',
        'desc': 'لوحة تحكم لتبسيط المهام، التقارير، ومتابعة الأداء.',
    },
    {
        'title': 'بنية شبكات مؤسسية',
        'category': 'شبكات واتصال',
        'tone': 'blue',
        'desc': 'تصميم شبكة مستقرة مع أمان وقابلية توسع.',
    },
    {
        'title': 'تطبيق خدمات العملاء',
        'category': 'تطبيقات رقمية',
        'tone': 'navy',
        'desc': 'تجربة استخدام سلسة لطلب الخدمات والمتابعة.',
    },
]


@require_http_methods(['GET', 'POST'])
def index(request):
    form = ContactForm()
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم استلام طلبك بنجاح. سيتواصل معك فريق زيد تك قريبًا.')
            return redirect(f"{request.path}#contact")
        messages.error(request, 'تعذّر إرسال النموذج. تحقق من الحقول وحاول مجددًا.')

    return render(request, 'website/index.html', {
        'site': SITE,
        'services': SERVICES,
        'why_us': WHY_US,
        'projects': PROJECTS,
        'contact_form': form,
        'whatsapp_url': f"https://wa.me/{SITE['whatsapp']}",
        'tel_url': f"tel:{SITE['phone']}",
        'mailto_url': f"mailto:{SITE['email']}",
    })
