from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0010_tarefa_area'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParticipacaoTarefa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inscrito_em', models.DateTimeField(auto_now_add=True)),
                ('tarefa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participacoes', to='usuarios.tarefa')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participacoes', to='usuarios.usuario')),
            ],
            options={
                'unique_together': {('usuario', 'tarefa')},
            },
        ),
    ]
