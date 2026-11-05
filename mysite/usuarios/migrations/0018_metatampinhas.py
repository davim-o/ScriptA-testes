from django.db import migrations, models
import django.db.models.deletion


def patch_constraints_and_clean_orphans(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor == 'sqlite':
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM usuarios_curtida WHERE publicacao_id NOT IN (SELECT id FROM usuarios_publicacao)"
            )
            cursor.execute(
                "DELETE FROM usuarios_curtida WHERE usuario_id NOT IN (SELECT id FROM usuarios_usuario)"
            )

        def safe_check_constraints():
            with conn.cursor() as cursor:
                cursor.execute("PRAGMA foreign_key_check(usuarios_metatampinhas)")
                violations = cursor.fetchall()
                if violations:
                    from django.db.utils import IntegrityError
                    raise IntegrityError(f"Constraint violations in usuarios_metatampinhas: {violations}")
        conn.check_constraints = safe_check_constraints


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0017_usuario_perfil'),
    ]

    operations = [
        migrations.RunPython(patch_constraints_and_clean_orphans, noop),
        migrations.CreateModel(
            name='MetaTampinhas',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meta_kg', models.DecimalField(decimal_places=3, default=40.0, max_digits=10)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('atualizado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='metas_tampinhas_definidas', to='usuarios.usuario')),
            ],
        ),
    ]
