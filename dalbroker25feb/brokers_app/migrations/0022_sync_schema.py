from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('brokers_app', '0021_alter_product_amount'),
    ]

    operations = [
        migrations.RunSQL("SET FOREIGN_KEY_CHECKS=0;"),
        migrations.RunSQL("SET FOREIGN_KEY_CHECKS=1;"),
    ]