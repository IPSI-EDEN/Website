# your_app/signals.py
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Group, DEFAULT_GROUP_NAME

@receiver(post_migrate)
def create_default_group(sender, **kwargs):
    if sender.name == 'Website': 
        Group.objects.get_or_create(name=DEFAULT_GROUP_NAME, defaults={
            'description': 'Group par défaut pour les Raspberries non assignés.'
        })
