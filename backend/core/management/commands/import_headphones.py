import json

from django.core.management.base import BaseCommand

from core.models import Headphone
from core.utils import HEADPHONES_PATH


class Command(BaseCommand):
    help = "Import headphones from the bundled JSON seed file."

    def handle(self, *args, **options):
        with open(HEADPHONES_PATH, "r", encoding="utf-8") as source:
            headphones = json.load(source)

        created_count = 0
        updated_count = 0

        for item in headphones:
            _, created = Headphone.objects.update_or_create(
                name=item["name"],
                defaults={
                    "type": item.get("type", ""),
                    "connection": item.get("connection", ""),
                    "max_db_spl_wired": item.get("max_dB_SPL_wired"),
                    "max_db_spl_bluetooth": item.get("max_dB_SPL_bluetooth"),
                    "notes": item.get("notes", ""),
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported headphones: {created_count} created, {updated_count} updated."
            )
        )
