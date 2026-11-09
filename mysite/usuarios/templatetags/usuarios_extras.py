import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

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


@register.filter(name="formatar_texto")
def formatar_texto(valor):
    """
    Renderiza formatação rica de texto (negrito, itálico, sublinhado, tachado,
    código, citações e listas) com proteção total contra XSS (escapa todo HTML bruto antes).
    """
    if not valor:
        return ""
    texto = escape(str(valor))

    # Inline formatting (operando sobre texto já escapado contra XSS)
    texto = re.sub(r"`([^`\n]+)`", r'<code class="rt-code">\1</code>', texto)
    texto = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", texto)
    texto = re.sub(r"__([^_\n]+)__", r"<u>\1</u>", texto)
    texto = re.sub(r"~~([^~\n]+)~~", r"<s>\1</s>", texto)
    texto = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", texto)

    linhas = texto.splitlines()
    linhas_formatadas = []
    for linha in linhas:
        l_strip = linha.lstrip()
        if l_strip.startswith("&gt; "):
            conteudo = l_strip[5:]
            linhas_formatadas.append(f'<span class="rt-quote">{conteudo}</span>')
        elif l_strip.startswith("• ") or l_strip.startswith("- "):
            conteudo = l_strip[2:]
            linhas_formatadas.append(f'<span class="rt-list-item"><span class="rt-bullet">•</span><span>{conteudo}</span></span>')
        else:
            linhas_formatadas.append(linha)

    return mark_safe("<br>".join(linhas_formatadas))
