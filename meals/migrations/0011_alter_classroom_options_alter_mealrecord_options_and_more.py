# Generated by Django 4.2.5 on 2025-04-20 16:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0010_mealrecord_non_eat_alter_mealrecord_meal_type'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='classroom',
            options={'verbose_name': 'Lớp học', 'verbose_name_plural': 'Lớp học'},
        ),
        migrations.AlterModelOptions(
            name='mealrecord',
            options={'verbose_name': 'Bữa ăn', 'verbose_name_plural': 'Bữa ăn'},
        ),
        migrations.AlterModelOptions(
            name='student',
            options={'verbose_name': 'Học sinh', 'verbose_name_plural': 'Học sinh'},
        ),
        migrations.AddField(
            model_name='mealrecord',
            name='absence_reason',
            field=models.TextField(blank=True, null=True, verbose_name='Lý do nghỉ'),
        ),
    ]
