from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0009_tarefa'),
    ]

    operations = [
        migrations.AddField(
            model_name='tarefa',
            name='area',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
