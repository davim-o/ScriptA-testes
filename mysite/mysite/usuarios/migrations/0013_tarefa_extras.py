from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0011_participacao_tarefa'),
    ]

    operations = [
        # Adicionar campos na Tarefa existente
        migrations.AddField(
            model_name='tarefa',
            name='imagem',
            field=models.ImageField(blank=True, null=True, upload_to='tarefas/'),
        ),
        migrations.AddField(
            model_name='tarefa',
            name='concluida',
            field=models.BooleanField(default=False),
        ),
        # Modelo ObservacaoTarefa
        migrations.CreateModel(
            name='ObservacaoTarefa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField()),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('tarefa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='observacoes', to='usuarios.tarefa')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='observacoes', to='usuarios.usuario')),
            ],
        ),
        # Modelo ConclusaoTarefa
        migrations.CreateModel(
            name='ConclusaoTarefa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagem', models.ImageField(blank=True, null=True, upload_to='conclusoes/')),
                ('comentario', models.TextField(blank=True)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('tarefa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conclusoes', to='usuarios.tarefa')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conclusoes', to='usuarios.usuario')),
            ],
            options={
                'unique_together': {('usuario', 'tarefa')},
            },
        ),
    ]
