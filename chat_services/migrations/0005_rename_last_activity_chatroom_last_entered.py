# Generated by Django 4.2.10 on 2024-02-22 15:06

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("chat_services", "0004_chatroom_last_activity"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chatroom",
            old_name="last_activity",
            new_name="last_entered",
        ),
    ]