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


def _aplicar_formatacao_inline(linha_escapada):
    linha_escapada = re.sub(r"`([^`\n]+)`", r'<code class="rt-code">\1</code>', linha_escapada)
    linha_escapada = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", linha_escapada)
    linha_escapada = re.sub(r"__([^_\n]+)__", r"<u>\1</u>", linha_escapada)
    linha_escapada = re.sub(r"~~([^~\n]+)~~", r"<s>\1</s>", linha_escapada)
    linha_escapada = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", linha_escapada)
    return linha_escapada


@register.filter(name="formatar_texto")
def formatar_texto(valor):
    """
    Renderiza formatação rica de texto preservando fielmente quebras de linha,
    linhas em branco, recuos e formatação inline com proteção total contra XSS.
    """
    if not valor:
        return ""
    texto_norm = str(valor).replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    texto_esc = escape(texto_norm)

    linhas = texto_esc.split("\n")
    linhas_formatadas = []
    for linha in linhas:
        recuo_len = len(linha) - len(linha.lstrip(" "))
        recuo_html = linha[:recuo_len]
        l_strip = linha[recuo_len:]

        if l_strip.startswith("&gt; ") or l_strip == "&gt;":
            conteudo = _aplicar_formatacao_inline(l_strip[5:] if l_strip.startswith("&gt; ") else "")
            linhas_formatadas.append(f'{recuo_html}<span class="rt-quote">{conteudo}</span>')
        elif l_strip.startswith("• ") or l_strip.startswith("- "):
            conteudo = _aplicar_formatacao_inline(l_strip[2:])
            linhas_formatadas.append(
                f'{recuo_html}<span class="rt-list-item"><span class="rt-bullet">•</span><span>{conteudo}</span></span>'
            )
        else:
            linhas_formatadas.append(_aplicar_formatacao_inline(linha))

    return mark_safe("<br>".join(linhas_formatadas))
