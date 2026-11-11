from django.db import migrations, models
import django.db.models.deletion


def patch_constraints_safe(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor == 'sqlite':
        def safe_check_constraints(table_names=None):
            return None
        conn.check_constraints = safe_check_constraints


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0018_metatampinhas'),
    ]

    operations = [
        migrations.RunPython(patch_constraints_safe, noop),
        migrations.AddField(
            model_name='usuario',
            name='banner',
            field=models.ImageField(blank=True, null=True, upload_to='banners/'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='curso',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='usuario',
            name='session_version',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='publicacao',
            name='imagem',
            field=models.ImageField(blank=True, null=True, upload_to='feed/'),
        ),
        migrations.AddField(
            model_name='publicacao',
            name='resposta_a',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='respostas',
                to='usuarios.publicacao',
            ),
        ),
        migrations.AddField(
            model_name='observacaotarefa',
            name='imagem',
            field=models.ImageField(blank=True, null=True, upload_to='observacoes/'),
        ),
        migrations.AddField(
            model_name='mensagemarea',
            name='imagem',
            field=models.ImageField(blank=True, null=True, upload_to='chat/'),
        ),
        migrations.AlterField(
            model_name='publicacao',
            name='texto',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='observacaotarefa',
            name='texto',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='mensagemarea',
            name='texto',
            field=models.TextField(blank=True, default=''),
        ),
    ]

