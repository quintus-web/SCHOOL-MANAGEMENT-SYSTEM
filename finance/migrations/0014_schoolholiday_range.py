from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_schoolholiday'),
    ]

    operations = [
        migrations.RenameField(
            model_name='schoolholiday',
            old_name='date',
            new_name='start_date',
        ),
        migrations.AddField(
            model_name='schoolholiday',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
