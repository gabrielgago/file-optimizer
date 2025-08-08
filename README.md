# File Optimizer (.fopt)

**File Optimizer** é uma ferramenta desenvolvida para **compactar arquivos grandes** e assim **liberar espaço de armazenamento** na sua máquina.  
Sempre que o usuário **executar um arquivo com a extensão `.fopt`**, o programa será chamado automaticamente, **descompactará e abrirá o arquivo original**, mantendo a versão compactada como principal.

---

## 🚀 Funcionalidades

- Varre pastas como Documentos, Downloads, Área de Trabalho e Imagens.
- Lista arquivos grandes acima de um tamanho mínimo (configurável).
- Compacta arquivos para o formato `.fopt` com alta compressão (`LZMA`).
- Ao clicar duas vezes em um `.fopt`, o programa descompacta, abre e apaga o arquivo após uso.
- Interface moderna inspirada no Windows, feita com HTML + Bootstrap + Fluent UI.

---

## 🛠️ Requisitos

Antes de rodar o projeto, instale os seguintes pré-requisitos:

- **Python 3.10+**
- **pip**
- Google Chrome (recomendado para a interface via Eel)

---

## 📦 Como instalar e rodar

1. **Clone o repositório**:

   ```bash
   git clone https://github.com/seu-usuario/file-optimizer.git
   cd file-optimizer
   ```

2. **Crie um ambiente virtual (opcional, mas recomendado)**:

   ```bash
   python -m venv venv
   venv\Scripts\activate  # no Windows
   ```

3. **Instale as dependências**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Rode o projeto**:

   ```bash
   python main.py
   ```

---

## 🧩 Associando arquivos `.fopt` ao seu programa

Para abrir arquivos `.fopt` automaticamente com o File Optimizer:

1. Clique com o botão direito em qualquer arquivo `.fopt` > **Abrir com** > **Escolher outro aplicativo**.
2. Selecione **`python.exe`** (ou crie um atalho que execute `main.py` com o arquivo como argumento).
3. Marque **"Sempre usar este aplicativo para abrir arquivos .fopt"**.

Opcionalmente, o sistema pode criar um **atalho visual com o ícone e nome do arquivo original** (em breve).

---

## 📁 Estrutura do Projeto

```
file-optimizer/
│
├── main.py               # Ponto de entrada do programa
├── optimizer.py          # Lógica de compressão/descompressão
├── interface/
│   ├── index.html        # Interface do usuário
│   ├── script.js         # Lógica de frontend
│   └── style.css         # Estilos personalizados
├── data.json             # Arquivo de controle de arquivos temporários
├── requirements.txt      # Dependências do projeto
└── README.md             # Este arquivo
```

---

## 📌 Observações

- Arquivos descompactados temporariamente são **apagados após 3 horas** automaticamente.
- A barra de progresso acompanha a compressão com precisão.
- O programa mantém um log detalhado no console para rastreamento de erros.

---

## ✨ Contribuição

Sugestões de melhorias, correções ou novos recursos são sempre bem-vindas.  
Você pode abrir um Pull Request ou relatar um problema na aba *Issues*.

---

## 🧠 Autor

Desenvolvido por **Gabriel Martins** – apaixonado por soluções que otimizam o dia a dia do usuário.