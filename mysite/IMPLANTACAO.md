# Relatório de Implantação em Nuvem — ScriptA

- **Status da Implantação**: ✅ **Concluída e em operação na nuvem**
- **URL Pública da Aplicação**: **[https://scripta.pythonanywhere.com](https://scripta.pythonanywhere.com)**
- **Serviço de Nuvem Utilizado**: **PythonAnywhere** (Plano Gratuito — *Beginner Account*)

Este documento registra todo o processo conduzido pela equipe para a implantação da aplicação **ScriptA** em um serviço de nuvem gratuito, contemplando:
1. A reunião e decisão conjunta da equipe sobre o provedor de nuvem;
2. O detalhamento passo a passo concreto executado na iteração atual até a entrada do sistema no ar;
3. Os impedimentos técnicos e limitações do plano gratuito encontrados e solucionados;
4. O plano de ação para a iteração seguinte (manutenção, atualização contínua e monitoramento em produção).

---

## 1. Reunião da Equipe e Decisão Conjunta do Serviço de Nuvem Gratuito

Conforme exigido na atividade, a equipe reuniu-se para avaliar as opções de serviços de nuvem com **plano gratuito (*Free Tier*)** capazes de hospedar uma aplicação **Python / Django** com banco de dados **SQLite** e upload de imagens.

### 1.1. Comparativo das Alternativas Discutidas em Reunião

| Serviço de Nuvem | Hospedagem Django Gratuita | Persistência de Dados (`db.sqlite3` e `media/`) | Exige Cartão de Crédito? | Análise da Equipe sobre o Plano Gratuito |
| :--- | :--- | :--- | :--- | :--- |
| **PythonAnywhere** *(Escolhido)* | **Sim** (Servidor WSGI nativo para Python) | **Sim** (512 MB de armazenamento persistente em disco) | **Não** | Melhor opção para o projeto: mantém os cadastros do SQLite e as fotos enviadas pelos alunos salvos permanentemente e não hiberna a cada 15 minutos. |
| **Render** | Sim (Web Service via Git) | **Não** (Disco efêmero no plano gratuito) | Não | No plano gratuito, o container entra em *spin-down* após 15 min sem uso e **apaga o arquivo `db.sqlite3` e a pasta `media/`** a cada reinicialização. |
| **Railway** | Apenas *Trial* | Parcial | Sim | O plano gratuito permanente foi descontinuado, restando apenas um crédito inicial temporário que expira rapidamente. |
| **Fly.io** | Restrito | Sim (via Volumes) | Sim | Exige cartão de crédito internacional para criação da conta, inviabilizando o uso compartilhado por toda a equipe estudantil. |

### 1.2. Decisão Final da Equipe

Por decisão conjunta, a equipe escolheu o **PythonAnywhere (Plano *Beginner*)**. Além de ser totalmente gratuito e acessível sem cartão de crédito, ele garante a **persistência real do banco `db.sqlite3` e dos arquivos de mídia (`media/`)**, permitindo que os alunos se cadastrem, enviem fotos de perfil e comprovem tarefas pelo celular ou computador sem perda de dados.

---

## 2. Detalhamento dos Passos Concretos Realizados na Iteração Atual

A equipe concluiu todas as etapas de preparação e implantação já nesta iteração, colocando o sistema em funcionamento em **[https://scripta.pythonanywhere.com](https://scripta.pythonanywhere.com)**. Abaixo estão todos os passos concretos executados:

### Passo 1 — Adaptação Responsiva (Mobile-First) e Refinamento de Interface
Antes de publicar na nuvem, a interface foi ajustada para funcionar em telas de diferentes proporções (celulares, tablets e desktops):
- Implementação de barra lateral (*sidebar*) retrátil com alça de arraste (*touch/drag*) para navegação no celular.
- Ajustes nas telas de Login e Cadastro: opção de visualizar senha ("olhinho"), mascotes alinhados horizontalmente com animação nos olhos e textos simplificados com mensagens *ghost* (*placeholders*).
- Alinhamento responsivo dos cartões e horários de tarefas nas telas de Área, Minhas Tarefas e Painel Administrativo.

### Passo 2 — Integração com Matrícula do SUAP e Padronização do Banco de Dados
- Implementação do módulo [`usuarios/suap.py`](usuarios/suap.py) para identificar automaticamente a **Diretoria** (`Diatinf`, `Diaren`, `Diacon` ou `Diacin`) e o **Curso** do aluno assim que a matrícula do SUAP é digitada no cadastro, preenchendo o campo de Diretoria de forma automática e bloqueada contra erros de seleção.
- Limpeza integral do banco de dados (`db.sqlite3`), deixando apenas as **4 contas oficiais dos líderes de diretoria**:
  - `Diatinf` (senha: `diatinf`)
  - `Diaren` (senha: `diaren`)
  - `Diacon` (senha: `diacon`)
  - `Diacin` (senha: `diacin`)

### Passo 3 — Preparação das Configurações do Django para Nuvem (`settings.py` e `urls.py`)
No arquivo [`mysite/settings.py`](mysite/settings.py) e em [`mysite/urls.py`](mysite/urls.py):
1. Inclusão do domínio `scripta.pythonanywhere.com` e `*.pythonanywhere.com` em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.
2. Configuração de `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` para compatibilidade com o proxy HTTPS da plataforma.
3. Uso de sessões em cookies assinados (`SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'`) para eliminar erros de concorrência (*database is locked*) no SQLite.
4. Configuração de `STATIC_ROOT = BASE_DIR / 'staticfiles'` e `MEDIA_ROOT = BASE_DIR / 'media'`, além de rota dedicada em `mysite/urls.py` para servir imagens enviadas pelos usuários.

### Passo 4 — Empacotamento e Upload para o Servidor PythonAnywhere
1. Criação da conta **`Scripta`** no PythonAnywhere.
2. Geração do pacote de implantação [`scripta_deploy.zip`](scripta_deploy.zip) formatado com separadores de diretório padrão Linux (`/`) e envio do arquivo pela aba **Files** para `/home/Scripta/`.
3. Execução dos comandos de extração, instalação de dependências e coleta de arquivos estáticos no **Bash Console** do PythonAnywhere:
   ```bash
   unzip -o scripta_deploy.zip -d ~/mysite && cd ~/mysite && pip install --user django pillow && python manage.py collectstatic --noinput
   ```

### Passo 5 — Configuração do Servidor WSGI e Mapeamento de Arquivos Estáticos
1. Criação da aplicação na aba **Web** utilizando **Manual configuration (Python 3.10)**.
2. Configuração do arquivo WSGI (`/var/www/scripta_pythonanywhere_com_wsgi.py`) apontando para o projeto:
   ```python
   import os
   import sys

   path = '/home/Scripta/mysite'
   if path not in sys.path:
       sys.path.append(path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
3. Mapeamento das pastas estáticas na seção **Static files** da aba **Web**:
   - **URL**: `/static/` → **Directory**: `/home/Scripta/mysite/staticfiles`
   - **URL**: `/media/` → **Directory**: `/home/Scripta/mysite/media`
4. Acionamento do botão **Reload `scripta.pythonanywhere.com`** e validação do sistema no ar.

---

## 3. Impedimentos Encontrados e Como Foram Solucionados

Durante a preparação e execução da implantação no plano gratuito, a equipe enfrentou os seguintes impedimentos técnicos:

1. **Bloqueio de Conexões Externas pelo Proxy do Plano Gratuito (API do SUAP)**:
   - **Impedimento**: Contas gratuitas do PythonAnywhere passam por um proxy restritivo que bloqueia requisições HTTP/HTTPS de saída para servidores externos que não façam parte da *whitelist* padrão da plataforma. Isso impede que o servidor em nuvem gratuita faça requisições diretas para a API de autenticação do SUAP (`suap.ifrn.edu.br`) no momento do cadastro.
   - **Solução Aplicada**: Desenvolvemos em [`usuarios/suap.py`](usuarios/suap.py) e [`usuarios/static/js/cadastro.js`](usuarios/static/js/cadastro.js) um mecanismo híbrido com *fallback* local. Quando o proxy gratuito bloqueia a comunicação direta com o SUAP, o sistema decodifica automaticamente a estrutura da matrícula do IFRN (ano, período e código do curso embutido na matrícula), identifica a **Diretoria** e o **Curso** instantaneamente e conclui a solicitação de cadastro normalmente, enviando o aluno para aprovação do líder de sua diretoria.

2. **Incompatibilidade de Separadores de Caminho em Arquivos `.zip` Windows vs. Linux**:
   - **Impedimento**: Ao compactar o projeto no Windows com ferramentas padrão do PowerShell (`Compress-Archive`), os caminhos internos do `.zip` utilizam barra invertida (`\`), o que gera falhas na criação de subpastas ao rodar `unzip` no servidor Linux do PythonAnywhere.
   - **Solução Aplicada**: O pacote [`scripta_deploy.zip`](scripta_deploy.zip) foi gerado convertendo todos os caminhos internos para barra normal (`/`) padrão POSIX/Linux, garantindo descompactação limpa em `/home/Scripta/mysite`.

3. **Travas de Concorrência do SQLite em Ambiente Compartilhado**:
   - **Impedimento**: O sistema de arquivos em rede do plano gratuito possui latência maior de I/O, o que pode causar o erro `OperationalError: database is locked` quando múltiplos usuários gravam sessões simultaneamente no SQLite.
   - **Solução Aplicada**: As sessões (`SESSION_ENGINE`) e mensagens (`MESSAGE_STORAGE`) foram transferidas do banco de dados para cookies assinados e o `timeout` do SQLite foi ampliado para 60 segundos.

4. **Limitações Estruturais do Plano Gratuito**:
   - Limite de **512 MB de armazenamento em disco** (exige atenção ao tamanho das imagens enviadas em `media/`).
   - Limite de **100 segundos de CPU por dia** em consoles interativos.
   - Necessidade de clicar no botão *Run until 3 months from today* no painel Web a cada 3 meses para manter o domínio gratuito ativo.

---

## 4. Plano de Ação para a Próxima Iteração

Com a aplicação já implantada e acessível em **[https://scripta.pythonanywhere.com](https://scripta.pythonanywhere.com)**, o plano de ação da equipe para a próxima iteração concentra-se na operação assistida, otimização de recursos do plano gratuito e evolução contínua:

- [ ] **1. Testes de Uso Real com Alunos e Líderes das 4 Diretorias**:
  - Compartilhar o link `https://scripta.pythonanywhere.com` com membros da equipe em diferentes dispositivos móveis para testar o fluxo completo: solicitação de cadastro com matrícula do SUAP → aprovação pelo líder da diretoria (`Diatinf`, `Diaren`, `Diacon`, `Diacin`) → promoção de sub-líderes → criação e conclusão de tarefas com foto.
- [ ] **2. Automatização da Atualização Contínua via GitHub no PythonAnywhere**:
  - Vincular o diretório `/home/Scripta/mysite` diretamente ao repositório remoto do GitHub para que novas alterações na próxima iteração sejam atualizadas apenas com `git pull && python manage.py migrate && python manage.py collectstatic --noinput`.
- [ ] **3. Compressão Automática de Imagens no Upload (`Pillow`)**:
  - Redimensionar e comprimir automaticamente as imagens enviadas no perfil e na entrega de tarefas para economizar a cota gratuita de 512 MB de disco do PythonAnywhere.
- [ ] **4. Rotina Periódica de Backup do Banco `db.sqlite3`**:
  - Realizar download periódico do arquivo `/home/Scripta/mysite/db.sqlite3` (ou exportação JSON via `dumpdata`) antes de cada atualização de versão da próxima iteração.
