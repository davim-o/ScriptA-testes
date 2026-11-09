# ScriptA — Plataforma de Organização de Torcidas e Equipes (IFRN)

O **ScriptA** é uma aplicação web responsiva desenvolvida em **Django** para organizar e integrar as torcidas e equipes das diretorias acadêmicas (**Diatinf**, **Diaren**, **Diacon** e **Diacin**) por áreas de atuação (*Cenário, Staff, Dança, Figurino, Sonoplastia, Tampinhas e Roteiro*).

---

## ☁️ Implantação em Nuvem (Documentação da Iteração)

Conforme solicitado na atividade da disciplina, todo o registro da reunião de escolha do serviço de nuvem gratuito, os passos concretos realizados pela equipe, os impedimentos encontrados no plano gratuito e o plano de ação para a próxima iteração estão detalhados no documento abaixo:

👉 **[📄 Acessar Relatório e Guia de Implantação em Nuvem (IMPLANTACAO.md)](./IMPLANTACAO.md)**

🌐 **Link da Aplicação na Nuvem (PythonAnywhere):** [https://scripta.pythonanywhere.com](https://scripta.pythonanywhere.com)

---

## 🔑 Contas dos Líderes das Diretorias

O banco de dados inicial está configurado e limpo exclusivamente com as 4 contas de administração (líderes de cada diretoria):

| Diretoria | Matrícula (Login) | Senha |
| :--- | :--- | :--- |
| **Diatinf** | `Diatinf` | `diatinf` |
| **Diaren** | `Diaren` | `diaren` |
| **Diacon** | `Diacon` | `diacon` |
| **Diacin** | `Diacin` | `diacin` |

> **Cadastro de Alunos (SUAP):** Os membros cadastram-se utilizando sua matrícula e senha do SUAP. O sistema identifica e preenche automaticamente a **Diretoria** correspondente à matrícula do aluno, puxa o nome do SUAP (editável posteriormente no perfil) e exibe o curso no perfil.

---

## 🚀 Principais Funcionalidades

- **Autenticação e Cadastro Integrado ao SUAP**: Identificação automática de diretoria e curso a partir da matrícula do aluno, com botão de visualização de senha e mascotes interativos.
- **Interface Totalmente Responsiva (Mobile & Desktop)**: Menu lateral deslizante com barra de arraste (*touch/drag*) para uso fluido em celulares.
- **Painel Administrativo por Diretoria e Sub-Liderança**:
  - Aprovação de novos membros por diretoria.
  - Promoção de sub-líderes por área de atuação.
  - Criação, edição, acompanhamento e encerramento de tarefas (rápidas com horário ou prolongadas com prazo).
- **Áreas de Atuação e Minhas Tarefas**:
  - Inscrição em tarefas com controle de vagas, envio de observações e entrega de comprovação por foto.
  - Chat exclusivo por área com suporte a respostas e curtidas.
- **Arrecadação e Ranking de Tampinhas**:
  - Registro de doações em gramas pelo sub-líder da área Tampinhas, definição de meta em Kg e ranking atualizado em tempo real.

---

## 🛠️ Como Executar o Projeto Localmente

1. **Acesse a pasta do projeto Django**:
   ```bash
   cd mysite
   ```

2. **Crie e ative um ambiente virtual (opcional, mas recomendado)**:
   ```bash
   python -m venv venv
   # Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # Linux / macOS:
   source venv/bin/activate
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Aplique as migrações e inicie o servidor**:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

5. **Acesse no navegador**:
   - `http://127.0.0.1:8000/`

