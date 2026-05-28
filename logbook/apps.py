from django.apps import AppConfig


class LogbookConfig(AppConfig):
    name = 'logbook'

    def ready(self):
        import logbook.signals
