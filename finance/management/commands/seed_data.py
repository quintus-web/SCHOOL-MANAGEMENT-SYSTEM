# finance/management/commands/seed_data.py
import os
import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from finance.models import Student, ClassStream, Subject

class Command(BaseCommand):
    help = "Parses the master school CSV dataset and seeds the SQLite database tables seamlessly."

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        csv_path = os.path.join(base_dir, "Crescent Heights School - STUDENTS.csv")

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"Data engine failure: CSV file not found at {csv_path}"))
            return

        self.stdout.write(self.style.WARNING("Starting Milestone 1: Data Engine Migration parsing pipeline..."))

        with open(csv_path, newline="", encoding="utf-8") as file:
            reader = csv.reader(file)
            header = next(reader, None)  # Skip table header column mapping

            student_count = 0
            stream_count = 0

            for row in reader:
                if not row or len(row) < 6:
                    continue

                # 1. Map columns from your standard spreadsheet layout
                adm_no = row[0].strip()
                full_name = row[1].strip()
                gender_raw = row[2].strip().upper()
                stream_name = row[5].strip()  # Column 6: Current Grade/Stream
                guardian = row[8].strip() if len(row) > 8 else "Not Provided"
                phone = row[9].strip() if len(row) > 9 else "0700000000"

                # Parse first and last names out cleanly
                name_parts = full_name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else "Ondicho"

                # Normalize gender parameter choices
                gender = 'F' if gender_raw in ['F', 'FEMALE', 'GIRL'] else 'M'

                # 2. Dynamically fetch or provision the Class Stream allocation object
                stream_instance, created = ClassStream.objects.get_or_create(name=stream_name)
                if created:
                    stream_count += 1

                # 3. Create or update the Student record database mapping row
                Student.objects.update_or_create(
                    admission_number=adm_no,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'gender': gender,
                        'class_stream': stream_instance,
                        'guardian_name': guardian,
                        'parent_phone': phone,
                        'current_balance': Decimal("0.00")  # Set clean default opening balance balances
                    }
                )
                student_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Milestone 1 Complete! Successfully provisioned {stream_count} new class streams and injected {student_count} student profile tables."
        ))