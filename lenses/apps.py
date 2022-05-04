from django.apps import AppConfig

class LensesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lenses'

    def ready(self):
        from actstream import registry
        #from django.contrib.auth.models import Group
        #registry.register(Group)
        registry.register(self.get_model('Lenses'))
        registry.register(self.get_model('Users'))
        registry.register(self.get_model('SledGroup'))
        registry.register(self.get_model('Collection'))
        registry.register(self.get_model('AdminCollection'))
