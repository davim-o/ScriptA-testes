#!/usr/bin/env python3.10
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

    # No GitHub Codespaces e contêineres, se o comando 'runserver' for executado
    # sem endereço/porta explícitos, vincula automaticamente a 0.0.0.0:8000 para
    # que o proxy de encaminhamento de portas do GitHub Codespaces não resulte em 404.
    if len(sys.argv) >= 2 and sys.argv[1] == 'runserver':
        if len(sys.argv) == 2:
            sys.argv.append('0.0.0.0:8000')
        elif len(sys.argv) == 3 and sys.argv[2].isdigit():
            sys.argv[2] = f'0.0.0.0:{sys.argv[2]}'

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
