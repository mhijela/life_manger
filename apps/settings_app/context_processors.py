def system_settings(request):
    from .models import SystemSettings
    return {'system_settings': SystemSettings.load()}
