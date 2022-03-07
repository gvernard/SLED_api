from django.apps import AppConfig
#from lenses.models import SledGroup

class LensesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lenses'

    def ready(self):
        from actstream import registry
        #registry.register('SledGroup')
        registry.register(self.get_model('SledGroup'))
