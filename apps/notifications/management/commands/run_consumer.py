from django.core.management.base import BaseCommand

from apps.notifications.consumers.rabbitmq_consumer import run_consumer


class Command(BaseCommand):
    help = "Start RabbitMQ consumer for sups_ecom events"

    def handle(self, *args, **options):
        self.stdout.write("Starting RabbitMQ consumer...")
        run_consumer()
