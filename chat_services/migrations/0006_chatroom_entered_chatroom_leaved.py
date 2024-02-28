# Generated by Django 4.2.10 on 2024-02-27 08:26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat_services", "0005_rename_last_activity_chatroom_last_entered"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatroom",
            name="entered",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="chatroom",
            name="leaved",
            field=models.BooleanField(default=True),
        ),
    ]