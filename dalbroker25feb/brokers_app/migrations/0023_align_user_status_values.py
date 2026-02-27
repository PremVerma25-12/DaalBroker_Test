from django.db import migrations, models


def forward_align_status_values(apps, schema_editor):
    DaalUser = apps.get_model('brokers_app', 'DaalUser')
    DaalUser.objects.filter(status='deactive').update(status='deactivated')
    DaalUser.objects.filter(account_status='deactive').update(account_status='deactivated')


def backward_align_status_values(apps, schema_editor):
    DaalUser = apps.get_model('brokers_app', 'DaalUser')
    DaalUser.objects.filter(status='deactivated').update(status='deactive')
    DaalUser.objects.filter(account_status='deactivated').update(account_status='deactive')


class Migration(migrations.Migration):

    dependencies = [
        ('brokers_app', '0022_sync_schema'),
    ]

    operations = [
        migrations.RunPython(forward_align_status_values, backward_align_status_values),
        migrations.AlterField(
            model_name='daaluser',
            name='account_status',
            field=models.CharField(
                choices=[('active', 'Active'), ('deactivated', 'Deactivated'), ('suspended', 'Suspended')],
                db_index=True,
                default='active',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='daaluser',
            name='status',
            field=models.CharField(
                choices=[('active', 'Active'), ('deactivated', 'Deactivated'), ('suspended', 'Suspended')],
                default='active',
                max_length=20,
            ),
        ),
    ]
