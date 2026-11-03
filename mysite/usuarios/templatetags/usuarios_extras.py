from django import template

register = template.Library()

CORES_AVATAR = [
    "avatar-chat-roxo",
    "avatar-chat-verde",
    "avatar-chat-escuro",
    "avatar-chat-azul",
]


@register.filter
def primeira_area(areas):
    if not areas:
        return ""
    lista = [a for a in areas.split(",") if a]
    return lista[0] if lista else ""


@register.filter
def cor_avatar(identificador):
    if not identificador:
        return "avatar-chat-escuro"
    s = str(identificador).strip()
    if not s:
        return "avatar-chat-escuro"
    idx = sum(ord(ch) for ch in s) % len(CORES_AVATAR)
    return CORES_AVATAR[idx]

