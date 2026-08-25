from django.urls import path
from .views import webhook_evolution
urlpatterns = [
    path('evolution/', webhook_evolution, name='webhook_evolution')
]
