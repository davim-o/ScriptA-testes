from django import template

register=template.Library()


@register.filter
def primeira_area(areas):
    """Retorna apenas a primeira área de uma lista separada por vírgulas."""

    if not areas:
        return ""

    lista=[a for a in areas.split(",") if a]

    return lista[0] if lista else ""
