# Generated by Django 4.2.10 on 2024-06-27 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('health_records', '0002_healthrecordimage_title_alter_healthrecordimage_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='healthrecordimage',
            name='title',
            field=models.TextField(blank=True, default='AI 분석을 하지 않은 이미지입니다'),
        ),
    ]
