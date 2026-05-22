
from django.apps import AppConfig

class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField' # Clears the primary key warnings cleanly
    name = 'finance'
