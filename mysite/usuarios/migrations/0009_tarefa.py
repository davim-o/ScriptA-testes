from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0008_usuario_sublider_de'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tarefa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('tipo', models.CharField(choices=[('fixa', 'Fixa'), ('prolongada', 'Prolongada')], default='fixa', max_length=20)),
                ('data', models.DateField(blank=True, null=True)),
                ('horario', models.TimeField(blank=True, null=True)),
                ('data_inicio', models.DateField(blank=True, null=True)),
                ('data_fim', models.DateField(blank=True, null=True)),
                ('descricao', models.TextField(blank=True)),
                ('limite_participantes', models.IntegerField(default=2)),
                ('encerrada', models.BooleanField(default=False)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('criada_por', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tarefas_criadas', to='usuarios.usuario')),
            ],
        ),
    ]
