# Generated by Django 4.2.10 on 2024-06-08 17:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('health_records', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='healthrecordimage',
            name='title',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='healthrecordimage',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
