# Generated by Django 5.1.7 on 2025-04-03 11:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0004_alter_task_answers'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='head_answers',
            field=models.JSONField(blank=True, default={'answers': 'ОТВЕТЫ', 'questions': 'ВОПРОСЫ'}, verbose_name='Заголовки вопросов-ответов'),
        ),
    ]
