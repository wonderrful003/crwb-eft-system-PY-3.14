from django.apps import AppConfig

class EftAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eft_app'
    
    def ready(self):
        """Import signals when app is ready"""
        import eft_app.permissions  # noqa