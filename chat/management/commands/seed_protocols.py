"""
Management command to seed default medical protocols
"""

from django.core.management.base import BaseCommand
from chat.services.protocol_service import ProtocolService


class Command(BaseCommand):
    help = 'Seed default medical protocols into the database'
    
    def handle(self, *args, **options):
        self.stdout.write('Seeding default protocols...')
        
        protocol_service = ProtocolService()
        count = protocol_service.seed_default_protocols()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully seeded {count} protocols')
        )
