# Generated by Django 4.2.5 on 2025-04-13 18:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0008_alter_studentpayment_amount_paid_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentpayment',
            name='previous_balance',
        ),
    ]
