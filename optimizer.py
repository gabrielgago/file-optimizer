import os
import json
import zipfile
import shutil
import subprocess
import threading
import eel
from pathlib import Path
from datetime import datetime
import logging
import re
from tqdm import tqdm


# Diretórios padrão
PASTAS_PADRAO = [
    os.path.join(Path.home(), "Downloads"),
    os.path.join(Path.home(), "Documents"),
    os.path.join(Path.home(), "Pictures"),
    os.path.join(Path.home(), "Desktop")
]

# Diretório para dados da aplicação
DIR_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ARQUIVO_DADOS = os.path.join(DIR_DADOS, "data.json")
DIR_TMP = os.path.join(DIR_DADOS, "tmp")
DIR_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

EXTENSOES_INCLUIDAS = {
    # Documentos
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.odt', '.ods', '.odp',
    '.pages', '.numbers', '.key', '.csv', '.epub', '.mobi', ".log", ".md", ".json", ".xml",
    
    # Imagens
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.raw', '.cr2', '.nef',
    '.heic', '.heif', '.psd', '.ai', '.indd',
    
    # Vídeos
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.m2ts',
    '.mts', '.ts',
    
    # Áudio
    '.mp3', '.wav', '.ogg', '.aac', '.flac', '.wma', '.m4a', '.aiff', '.alac',
    
    # Outros
    '.pst', '.ost', '.mbox', '.eml'  # Arquivos de email e outros
}

cancelar_varredura = False
varredura_thread = None

eel.init(DIR_WEB)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

def e_arquivo_midia(caminho):
    extensao = os.path.splitext(caminho)[1].lower()
    return extensao in EXTENSOES_INCLUIDAS

def bytes_para_mb(bytes_):
    return round(bytes_ / (1024 ** 2), 2)

def bytes_para_gb(bytes_):
    return round(bytes_ / (1024 ** 3), 2)

def formatar_tamanho(bytes_):
    mb = bytes_para_mb(bytes_)
    gb = bytes_para_gb(bytes_)
    if gb < 0.1:
        return f"{mb} MB"
    else:
        return f"{mb} MB ({gb} GB)"

@eel.expose
def cancelar_varredura_js():
    global cancelar_varredura
    logging.info("Recebido comando para cancelar varredura via frontend.")
    cancelar_varredura = True
    # Aguarda thread terminar
    if varredura_thread and varredura_thread.is_alive():
        logging.info("Aguardando thread de varredura finalizar...")
        varredura_thread.join(timeout=2)
    return True

@eel.expose
def varrer_arquivos_js(tamanho_minimo_mb, pastas=None):
    global varredura_thread, cancelar_varredura
    logging.info(f"Recebido comando para iniciar varredura via frontend. Tamanho mínimo: {tamanho_minimo_mb} MB")
    cancelar_varredura = False
    # Se já existe uma thread rodando, não inicia outra
    if varredura_thread and varredura_thread.is_alive():
        logging.info("Já existe uma varredura em andamento, ignorando novo pedido.")
        return False
    varredura_thread = threading.Thread(target=fazer_varredura, args=(int(tamanho_minimo_mb), pastas), daemon=True)
    varredura_thread.start()
    return True

def fazer_varredura(tamanho_minimo_mb, pastas=None):
    global cancelar_varredura
    if pastas is None or not pastas:
        pastas = PASTAS_PADRAO

    arquivos_grandes = []
    arquivos_filtrados = 0
    arquivos_midia = 0

    def adicionar_log(mensagem):
        # Só envia logs relevantes ao usuário
        if (
            mensagem.startswith('Iniciando varredura nas pastas selecionadas') or
            mensagem.startswith('Varredura na pasta:') or
            mensagem.startswith('ENCONTRADO:') or
            mensagem.startswith('Varredura concluída') or
            mensagem.startswith('Varredura cancelada pelo usuário') or
            mensagem.startswith('Erro')
        ):
            try:
                eel.atualizar_progresso_multiplo([mensagem])
            except:
                pass
        logging.info(mensagem)

    adicionar_log("Iniciando varredura nas pastas selecionadas...")
    total_arquivos = 0
    arquivos_por_pasta = {}
    for pasta in pastas:
        arquivos_por_pasta[pasta] = []
        adicionar_log(f"Varredura na pasta: {os.path.basename(pasta)}")
        for root, _, files in os.walk(pasta):
            for file in files:
                if cancelar_varredura:
                    adicionar_log("Varredura cancelada pelo usuário.")
                    try:
                        eel.finalizar_varredura_cancelada()
                    except:
                        pass
                    return
                caminho = os.path.join(root, file)
                arquivos_por_pasta[pasta].append(caminho)
                total_arquivos += 1

    adicionar_log(f"Total de arquivos para analisar: {total_arquivos}")

    analisados = 0
    for pasta in pastas:
        if cancelar_varredura:
            adicionar_log("Varredura cancelada pelo usuário.")
            try:
                eel.finalizar_varredura_cancelada()
            except:
                pass
            return
        adicionar_log(f"Iniciando análise dos arquivos da pasta: {os.path.basename(pasta)}")
        for caminho in arquivos_por_pasta[pasta]:
            if cancelar_varredura:
                adicionar_log("Varredura cancelada pelo usuário.")
                try:
                    eel.finalizar_varredura_cancelada()
                except:
                    pass
                return
            analisados += 1
            try:
                if not os.path.isfile(caminho):
                    continue
                if not e_arquivo_midia(caminho):
                    arquivos_filtrados += 1
                    continue
                arquivos_midia += 1
                tamanho = os.path.getsize(caminho)
                tamanho_formatado = formatar_tamanho(tamanho)
                if tamanho >= tamanho_minimo_mb * 1024 * 1024:
                    pasta_base = os.path.basename(pasta)
                    nome_arquivo = os.path.basename(caminho)
                    nome_exibicao = f"{pasta_base}/{nome_arquivo}"
                    tipo = os.path.splitext(caminho)[1].upper()
                    arquivos_grandes.append({
                        "caminho": caminho,
                        "nome": nome_exibicao,
                        "tamanho": tamanho,
                        "tamanho_formatado": tamanho_formatado,
                        "tipo": tipo
                    })
                    adicionar_log(f"ENCONTRADO: {nome_exibicao} ({tamanho_formatado})")
                    try:
                        eel.atualizar_lista_arquivos(arquivos_grandes)
                    except:
                        pass
                progresso = int((analisados / total_arquivos) * 100)
                try:
                    eel.atualizar_barra_progresso(progresso)
                except:
                    pass
            except Exception as e:
                erro = f"Erro ao acessar {os.path.basename(caminho)}: {e}"
                adicionar_log(erro)

    if not cancelar_varredura:
        logging.info("Varredura concluída.")
        adicionar_log(f"Varredura concluída! Analisados {arquivos_midia} arquivos de mídia/documentos.")
        adicionar_log(f"Encontrados {len(arquivos_grandes)} arquivos grandes.")
        arquivos_grandes.sort(key=lambda x: x["tamanho"], reverse=True)
        try:
            eel.atualizar_lista_arquivos(arquivos_grandes)
            eel.finalizar_varredura()
        except:
            pass

@eel.expose
def carregar_dados_js():
    if not os.path.exists(ARQUIVO_DADOS):
        return {}
    with open(ARQUIVO_DADOS, "r") as f:
        return json.load(f)

def salvar_dados(dados):
    logging.info(f"Salvando dados em {ARQUIVO_DADOS}: {json.dumps(dados, indent=2)}")
    os.makedirs(DIR_DADOS, exist_ok=True)
    with open(ARQUIVO_DADOS, "w") as f:
        json.dump(dados, f, indent=2)
    logging.info("Dados salvos com sucesso.")

# Funções relacionadas ao diretório de destino foram removidas pois
# agora os arquivos são salvos no mesmo diretório dos originais

# A função compactar_arquivo_js foi removida pois agora utilizamos
# apenas a função compactar_arquivo_fopt_js que salva os arquivos
# no mesmo diretório com extensão .fopt
@eel.expose
def atualizarProgresso(p):
    pass  # Isso só precisa existir para o frontend chamar de volta se quiser

@eel.expose
def compactar_arquivo_fopt_js(caminho):
    """
    Compacta o arquivo na mesma pasta com extensão .fopt em uma thread separada.
    Utiliza compressão ZIP LZMA sem perdas.
    """

    def compactar():
        nome_arquivo = os.path.basename(caminho)
        pasta_origem = os.path.dirname(caminho)
        nome_fopt = os.path.splitext(nome_arquivo)[0] + ".fopt"
        destino = os.path.join(pasta_origem, nome_fopt)

        try:
            logging.info(f"Iniciando compactação do arquivo: {caminho} para {destino}")
            tamanho_total = os.path.getsize(caminho)

            with zipfile.ZipFile(destino, 'w', compression=zipfile.ZIP_LZMA) as zipf:
                zinfo = zipfile.ZipInfo(nome_arquivo)
                zinfo.compress_type = zipfile.ZIP_LZMA

                tamanho_total = os.path.getsize(caminho)
                total_lido = 0
                ultima_porcentagem = -1  # Para evitar chamadas repetidas

                with open(caminho, 'rb') as f_in:
                    with zipf.open(zinfo, 'w') as f_out:
                        with tqdm(total=tamanho_total, unit='B', unit_scale=True, desc="Compactando") as pbar:
                            while True:
                                chunk = f_in.read(1024 * 1024)  # 1MB
                                if not chunk:
                                    break
                                f_out.write(chunk)
                                total_lido += len(chunk)
                                pbar.update(len(chunk))

                                porcentagem = int((total_lido / tamanho_total) * 100)
                                if porcentagem != ultima_porcentagem:
                                    eel.atualizar_progress_bar(porcentagem)
                                    ultima_porcentagem = porcentagem

            logging.info(f"Arquivo compactado e salvo em: {destino}")

            # Salvar nos dados para manter compatibilidade
            dados = carregar_dados_js()
            dados[nome_fopt] = {
                "original": caminho,
                "compactado": destino,
                "data": datetime.now().isoformat()
            }
            salvar_dados(dados)

            # Tenta remover o arquivo original
            try:
                os.remove(caminho)
                logging.info(f"Arquivo original removido: {caminho}")
            except Exception as e:
                logging.warning(f"Não foi possível remover o arquivo original: {e}")

            # Callback via EEL
            eel._compactar_arquivo_fopt_callback({
                "sucesso": True,
                "mensagem": f"Arquivo compactado com sucesso: {destino}",
                "destino": destino
            })

        except Exception as e:
            logging.error(f"Erro ao compactar arquivo: {str(e)}")
            eel._compactar_arquivo_fopt_callback({
                "sucesso": False,
                "mensagem": f"Erro ao compactar arquivo: {str(e)}"
            })

    threading.Thread(target=compactar, daemon=True).start()
    return None  # O resultado será enviado via callback

@eel.expose
def _compactar_arquivo_fopt_callback(resultado):
    # Função dummy para callback do eel, chamada pelo Python
    pass

# def criar_link_para_abrir(caminho_original, nome_fopt):
#     logging.info(f"Criando link para abrir/descompactar: {caminho_original} -> {nome_fopt}")
#     pasta = os.path.dirname(caminho_original)
#     nome_link = os.path.basename(caminho_original)
#     caminho_link = os.path.join(pasta, nome_link + ".url")
#     programa = os.path.abspath(__file__)
#     conteudo = f"""[InternetShortcut]
# URL=file:///{programa} {nome_fopt}
# IconFile={caminho_link}
# """
#     with open(caminho_link, "w") as f:
#         f.write(conteudo)
#     logging.info(f"Link criado em: {caminho_link}")

@eel.expose
def abrir_descompactar_arquivo_js(destino_arquivo, nome_original):
    logging.info(f"Solicitado abrir/descompactar: {destino_arquivo} para {nome_original}")
    os.makedirs(DIR_TMP, exist_ok=True)
    nome_tmp = os.path.basename(nome_original)
    destino_tmp = os.path.join(DIR_TMP, nome_tmp)
    dados = carregar_dados_js()
    nome_arquivo = os.path.basename(destino_arquivo)
    info = dados.get(nome_arquivo)

    ja_descompactado = (
        info and
        "tmp" in info and
        os.path.exists(info["tmp"])
    )

    # Sempre abrir maximizado no Windows
    def abrir_maximizado(path):
        if os.name == 'nt':
            logging.info(f"Abrindo arquivo (Windows/maximizado): {path}")
            import ctypes
            SW_MAXIMIZE = 3
            ctypes.windll.shell32.ShellExecuteW(None, "open", path, None, None, SW_MAXIMIZE)
        elif os.name == 'posix':
            logging.info(f"Abrindo arquivo (POSIX): {path}")
            subprocess.call(('open', path) if os.uname().sysname == 'Darwin' else ('xdg-open', path))

    if ja_descompactado:
        logging.info(f"Arquivo já descompactado em tmp: {info['tmp']}")
        try:
            abrir_maximizado(info["tmp"])
            return {"sucesso": True, "mensagem": f"Arquivo aberto com sucesso !"}
        except Exception as e:
            logging.error(f"Erro ao abrir arquivo já descompactado: {str(e)}")
            return {"sucesso": False, "mensagem": f"Erro ao abrir arquivo: {str(e)}"}
    try:
        logging.info(f"Descompactando {destino_arquivo} para {destino_tmp}")
        with zipfile.ZipFile(destino_arquivo, 'r') as zipf:
            zipf.extract(nome_tmp, DIR_TMP)
        extraido = os.path.join(DIR_TMP, nome_tmp)
        if info is not None:
            info["tmp"] = extraido
            info["data_descompressao"] = datetime.now().isoformat()
            salvar_dados(dados)
            logging.info(f"Atualizado JSON com caminho tmp: {extraido} e data de descompressao: {info['data_descompressao']}")
        abrir_maximizado(extraido)
        logging.info(f"Arquivo descompactado e aberto: {extraido}")
        return {"sucesso": True, "mensagem": f"Arquivo aberto com sucesso !"}
    except Exception as e:
        logging.error(f"Erro ao descompactar/abrir: {str(e)}")
        return {"sucesso": False, "mensagem": f"Erro ao descompactar/abrir: {str(e)}"}

@eel.expose
def limpar_tmp_antigos_js():
    logging.info("Limpando arquivos antigos da pasta tmp...")
    if not os.path.exists(DIR_TMP):
        logging.info("Pasta tmp não existe, nada para limpar.")
        return
    hoje = datetime.now().strftime("%Y-%m-%d")
    dados = carregar_dados_js()
    alterado = False

    # Remove arquivos da pasta tmp e metadados apenas se data_descompressao for anterior ao dia atual
    for nome_zip, info in list(dados.items()):
        tmp_path = info.get("tmp")
        data_descompressao = info.get("data_descompressao")
        if tmp_path and data_descompressao:
            try:
                data_str = data_descompressao[:10]
                if data_str < hoje and os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    logging.info(f"Removido arquivo antigo de tmp: {tmp_path}")
                    info.pop("tmp", None)
                    info.pop("data_descompressao", None)
                    alterado = True
                elif not os.path.exists(tmp_path):
                    info.pop("tmp", None)
                    info.pop("data_descompressao", None)
                    alterado = True
            except Exception as e:
                logging.warning(f"Erro ao remover tmp antigo: {e}")

    if alterado:
        salvar_dados(dados)

@eel.expose
def listar_pastas_sistema_js():
    logging.info("Listando pastas do sistema...")
    home = str(Path.home())
    pastas = []
    try:
        for item in os.listdir(home):
            caminho = os.path.join(home, item)
            if os.path.isdir(caminho):
                pastas.append(caminho)
    except Exception as e:
        logging.warning(f"Erro ao listar pastas do sistema: {e}")
    for pasta_padrao in PASTAS_PADRAO:
        if pasta_padrao not in pastas and os.path.isdir(pasta_padrao):
            pastas.append(pasta_padrao)
    logging.info(f"Pastas encontradas: {pastas}")
    return pastas

@eel.expose
def logando(msg):
    logging.info(f"LOG FRONTEND: {msg}")
    return True

def main():
    logging.info("Iniciando aplicação...")
    os.makedirs(DIR_DADOS, exist_ok=True)
    os.makedirs(DIR_TMP, exist_ok=True)
    logging.info("Diretórios principais garantidos/criados.")
    limpar_tmp_antigos_js()
    if not os.path.exists(DIR_WEB):
        os.makedirs(DIR_WEB)
        criar_arquivos_web()
        logging.info("Arquivos web criados.")
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        win_width, win_height = 950, 700
        pos_x = int((screen_width - win_width) / 2)
        pos_y = int((screen_height - win_height) / 2)
        logging.info(f"Posição da janela: {pos_x}, {pos_y}")
    except Exception as e:
        logging.warning(f"Erro ao obter posição da janela: {e}")
        pos_x, pos_y = None, None
    eel.start('index.html', size=(950, 700), position=(pos_x, pos_y))

def criar_arquivos_web():
    # Criar HTML
    html = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compactador de Documentos e Mídias</title>
    <link rel="stylesheet" href="https://static2.sharepointonline.com/files/fabric/office-ui-fabric-core/11.0.0/css/fabric.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fluentui/web-components/dist/web-components.min.css">
    <link rel="stylesheet" href="style.css">
    <script src="https://cdn.jsdelivr.net/npm/@fluentui/web-components/dist/web-components.min.js"></script>
    <script type="text/javascript" src="/eel.js"></script>
</head>
<body class="ms-Fabric">
    <div class="container">
        <header>
            <h1 class="ms-font-su">Compactador de Documentos e Mídias</h1>
            <p class="ms-font-l">Encontre e compacte seus arquivos grandes para economizar espaço</p>
        </header>

        <div class="main-content">
            <div class="tabs">
                <fluent-tabs activeid="tab1">
                    <fluent-tab-panel id="panel-1">
                        <div class="panel-content">
                            <div class="search-section">
                                <h2 class="ms-font-xl">Buscar arquivos grandes</h2>
                                <div class="search-controls">
                                    <fluent-text-field appearance="filled" placeholder="Tamanho mínimo em MB" id="tamanho-minimo" value="250"></fluent-text-field>
                                    <button id="btn-buscar" class="botao-busca">Buscar Arquivos</button>
                                </div>
                            </div>
                            
                            <div class="progress-section" id="progress-section" style="display: none;">
                                <h3 class="ms-font-l">Progresso da varredura</h3>
                                <fluent-progress id="progress-bar"></fluent-progress>
                                <div class="log-container ms-depth-8" id="log-container">
                                    <div id="log-content"></div>
                                </div>
                            </div>
                            
                            <div class="files-section" id="files-section" style="display: none;">
                                <h3 class="ms-font-l">Arquivos encontrados</h3>
                                <div class="files-container ms-depth-8">
                                    <table class="ms-Table">
                                        <thead>
                                            <tr>
                                                <th>Nome</th>
                                                <th>Tamanho</th>
                                                <th>Tipo</th>
                                                <th>Ações</th>
                                            </tr>
                                        </thead>
                                        <tbody id="files-table-body">
                                            <!-- Arquivos serão adicionados aqui dinamicamente -->
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </fluent-tab-panel>
                    
                    <fluent-tab-panel id="panel-2">
                        <div class="panel-content">
                            <h2 class="ms-font-xl">Arquivos compactados disponíveis</h2>
                            <div class="files-container ms-depth-8">
                                <table class="ms-Table">
                                    <thead>
                                        <tr>
                                            <th>Nome</th>
                                            <th>Data</th>
                                            <th>Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody id="compressed-files-table">
                                        <!-- Arquivos compactados serão adicionados aqui dinamicamente -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </fluent-tab-panel>
                </fluent-tabs>
            </div>
        </div>
        
        <footer>
            <p class="ms-font-s">v2.0 - Interface moderna com Fluent UI</p>
        </footer>
    </div>
    
    <!-- Diálogos -->
    <fluent-dialog id="compactar-dialog" hidden>
        <div class="dialog-content">
            <h2 class="ms-font-l">Compactando arquivo...</h2>
            <fluent-progress></fluent-progress>
        </div>
    </fluent-dialog>
    
    <script src="script.js"></script>
</body>
</html>
'''

    # Criar CSS
    css = '''/* Estilos gerais */
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background-color: #f3f2f1;
    color: #323130;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
}

header {
    margin-bottom: 30px;
    text-align: center;
    padding: 20px 0;
}

header h1 {
    margin-bottom: 10px;
    color: #0078d4;
}

.main-content {
    background-color: white;
    border-radius: 4px;
    box-shadow: 0 1.6px 3.6px 0 rgba(0, 0, 0, 0.132), 0 0.3px 0.9px 0 rgba(0, 0, 0, 0.108);
    padding: 20px;
    margin-bottom: 20px;
}

.panel-content {
    padding: 20px 0;
}

.search-section, .progress-section, .files-section {
    margin-bottom: 30px;
}

.search-controls {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

fluent-text-field {
    width: 200px;
}

/* Estilo para o botão de busca/cancelar */
.botao-busca {
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 2px;
    padding: 8px 16px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 14px;
    cursor: pointer;
    transition: background-color 0.2s, transform 0.1s;
    min-width: 140px;
    height: 32px;
    font-weight: 600;
}

.botao-busca:hover {
    background-color: #106ebe;
}

.botao-busca:active {
    transform: scale(0.98);
}

.botao-busca.cancelar {
    background-color: #d13438;
}

.botao-busca.cancelar:hover {
    background-color: #a4262c;
}

.log-container {
    height: 200px;
    overflow-y: auto;
    padding: 10px;
    background-color: #f9f9f9;
    border: 1px solid #e1e1e1;
    border-radius: 4px;
    margin-top: 10px;
    font-family: 'Consolas', monospace;
    font-size: 13px;
}

#log-content {
    white-space: pre-wrap;
}

.files-container {
    max-height: 400px;
    overflow-y: auto;
    margin-top: 15px;
    border: 1px solid #e1e1e1;
    border-radius: 4px;
}

.ms-Table {
    width: 100%;
    border-collapse: collapse;
}

.ms-Table th {
    background-color: #f3f2f1;
    padding: 10px;
    text-align: left;
    font-weight: 600;
    border-bottom: 1px solid #e1e1e1;
}

.ms-Table td {
    padding: 10px;
    border-bottom: 1px solid #e1e1e1;
}

.action-buttons {
    display: flex;
    gap: 5px;
}

footer {
    text-align: center;
    color: #605e5c;
    padding: 10px 0;
}

/* Estilo para mensagens no log */
.log-info {
    color: #0078d4;
}

.log-success {
    color: #107c10;
}

.log-error {
    color: #d13438;
}

.log-warning {
    color: #ffaa44;
}

/* Dialog styles */
.dialog-content {
    padding: 20px;
    min-width: 400px;
}

fluent-dialog h2 {
    margin-bottom: 20px;
}
'''

    # Criar JavaScript
    js = '''// Variáveis globais
let arquivosEncontrados = [];
let arquivoSelecionado = null;
let varreduraEmAndamento = false;

// Elementos da UI
const btnBuscar = document.getElementById('btn-buscar');
const tamanhoMinimo = document.getElementById('tamanho-minimo');
const progressSection = document.getElementById('progress-section');
const progressBar = document.getElementById('progress-bar');
const logContainer = document.getElementById('log-container');
const logContent = document.getElementById('log-content');
const filesSection = document.getElementById('files-section');
const filesTableBody = document.getElementById('files-table-body');
const compressedFilesTable = document.getElementById('compressed-files-table');
const compactarDialog = document.getElementById('compactar-dialog');

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar evento de clique para o botão buscar/cancelar
    btnBuscar.addEventListener('click', toggleVarredura);
    
    // Carregar arquivos compactados
    carregarArquivosCompactados();
});

// Função para alternar entre iniciar e cancelar varredura
function toggleVarredura() {
    if (varreduraEmAndamento) {
        // Cancelar varredura
        eel.cancelar_varredura_js();
        // O botão só será restaurado quando a varredura for completamente cancelada
        // Isso acontece na função finalizar_varredura_cancelada
    } else {
        // Iniciar varredura
        iniciarVarredura();
    }
}

// Funções expostas para o Eel (JavaScript -> Python)
eel.expose(atualizar_progresso);
function atualizar_progresso(mensagem) {
    const logItem = document.createElement('div');
    
    // Adicionar classe de estilo com base no conteúdo da mensagem
    if (mensagem.includes('ENCONTRADO')) {
        logItem.className = 'log-success';
    } else if (mensagem.includes('Erro')) {
        logItem.className = 'log-error';
    } else if (mensagem.includes('Ignorados')) {
        logItem.className = 'log-warning';
    } else {
        logItem.className = 'log-info';
    }
    
    logItem.textContent = mensagem;
    logContent.appendChild(logItem);
    
    // Rolar para o final
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Nova função para receber múltiplas mensagens de uma vez
eel.expose(atualizar_progresso_multiplo);
function atualizar_progresso_multiplo(mensagens) {
    for (const mensagem of mensagens) {
        atualizar_progresso(mensagem);
    }
}

eel.expose(atualizar_barra_progresso);
function atualizar_barra_progresso(valor) {
    progressBar.setAttribute('value', valor);
}

eel.expose(atualizar_lista_arquivos);
function atualizar_lista_arquivos(arquivos) {
    arquivosEncontrados = arquivos;
    
    // Limpar tabela
    filesTableBody.innerHTML = '';
    
    // Adicionar arquivos à tabela
    arquivos.forEach(arquivo => {
        const tr = document.createElement('tr');
        
        // Coluna Nome
        const tdNome = document.createElement('td');
        tdNome.textContent = arquivo.nome;
        tr.appendChild(tdNome);
        
        // Coluna Tamanho
        const tdTamanho = document.createElement('td');
        tdTamanho.textContent = arquivo.tamanho_formatado;
        tr.appendChild(tdTamanho);
        
        // Coluna Tipo
        const tdTipo = document.createElement('td');
        tdTipo.textContent = arquivo.tipo;
        tr.appendChild(tdTipo);
        
        // Coluna Ações
        const tdAcoes = document.createElement('td');
        const btnCompactar = document.createElement('fluent-button');
        btnCompactar.textContent = 'Compactar';
        btnCompactar.appearance = 'accent';
        btnCompactar.addEventListener('click', () => {
            compactarArquivo(arquivo.caminho);
        });
        tdAcoes.appendChild(btnCompactar);
        tr.appendChild(tdAcoes);
        
        filesTableBody.appendChild(tr);
    });
    
    // Mostrar seção de arquivos
    filesSection.style.display = 'block';
}

eel.expose(finalizar_varredura);
function finalizar_varredura() {
    // Finalizar barra de progresso
    progressBar.setAttribute('value', '100');
    
    // Restaurar botão para estado inicial
    restaurarBotaoBusca();
}

// Nova função para lidar com o cancelamento da varredura
eel.expose(finalizar_varredura_cancelada);
function finalizar_varredura_cancelada() {
    // Restaurar botão para estado inicial
    restaurarBotaoBusca();
}

// Função para restaurar o botão de busca
function restaurarBotaoBusca() {
    varreduraEmAndamento = false;
    btnBuscar.textContent = 'Buscar Arquivos';
    btnBuscar.classList.remove('cancelar');
}

// Funções de interface
function iniciarVarredura() {
    // Marcar que varredura está em andamento
    varreduraEmAndamento = true;
    
    // Mudar o botão para modo cancelar
    btnBuscar.textContent = 'Cancelar';
    btnBuscar.classList.add('cancelar');
    
    // Limpar log anterior
    logContent.innerHTML = '';
    
    // Limpar tabela de arquivos
    filesTableBody.innerHTML = '';
    
    // Mostrar seção de progresso
    progressSection.style.display = 'block';
    
    // Ocultar seção de arquivos até que a busca termine
    filesSection.style.display = 'none';
    
    // Resetar barra de progresso
    progressBar.removeAttribute('value');
    
    // Obter tamanho mínimo
    const tamanhoMinimoValor = parseInt(tamanhoMinimo.value) || 250;
    
    // Chamar função Python para varrer arquivos
    eel.varrer_arquivos_js(tamanhoMinimoValor);
}

async function compactarArquivo(caminho) {
    // Mostrar diálogo de compactação
    compactarDialog.hidden = false;
    
    // Chamar função Python para compactar arquivo
    const resultado = await eel.compactar_arquivo_js(caminho)();
    
    // Ocultar diálogo
    compactarDialog.hidden = true;
    
    // Mostrar resultado
    if (resultado.sucesso) {
        // Exibir mensagem de sucesso
        alert(resultado.mensagem);
        
        // Recarregar lista de arquivos compactados
        carregarArquivosCompactados();
    } else {
        // Exibir mensagem de erro
        alert(resultado.mensagem);
    }
}

async function carregarArquivosCompactados() {
    // Limpar tabela
    compressedFilesTable.innerHTML = '';
    
    // Carregar dados do Python
    const dados = await eel.carregar_dados_js()();
    
    // Verificar se há arquivos
    if (Object.keys(dados).length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.textContent = 'Nenhum arquivo compactado encontrado';
        td.colSpan = 3;
        td.style.textAlign = 'center';
        tr.appendChild(td);
        compressedFilesTable.appendChild(tr);
        return;
    }
    
    // Adicionar arquivos à tabela
    for (const [nomeZip, info] of Object.entries(dados)) {
        const tr = document.createElement('tr');
        
        // Coluna Nome
        const tdNome = document.createElement('td');
        tdNome.textContent = nomeZip;
        tr.appendChild(tdNome);
        
        // Coluna Data
        const tdData = document.createElement('td');
        try {
            const data = new Date(info.data);
            tdData.textContent = data.toLocaleString();
        } catch {
            tdData.textContent = info.data || 'Data desconhecida';
        }
        tr.appendChild(tdData);
        
        // Coluna Ações
        const tdAcoes = document.createElement('td');
        const btnAbrir = document.createElement('fluent-button');
        btnAbrir.textContent = 'Abrir';
        btnAbrir.appearance = 'accent';
        btnAbrir.addEventListener('click', () => {
            abrirArquivoCompactado(nomeZip);
        });
        tdAcoes.appendChild(btnAbrir);
        tr.appendChild(tdAcoes);
        
        compressedFilesTable.appendChild(tr);
    }
}

async function abrirArquivoCompactado(nomeZip) {
    const resultado = await eel.extrair_e_abrir_js(nomeZip)();
    
    if (resultado.sucesso) {
        alert(resultado.mensagem);
        
        // Armazenar caminho do arquivo temporário para posterior remoção
        const caminho = resultado.caminho;
        
        // Perguntar quando terminar de usar
        setTimeout(() => {
            if (confirm('Já terminou de usar o arquivo? Ele será removido quando confirmar.')) {
                eel.remover_arquivo_temporario(caminho);
            }
        }, 10000);  // Perguntar após 10 segundos
    } else {
        alert(resultado.mensagem);
    }
}
'''

    # Criar os arquivos
    with open(os.path.join(DIR_WEB, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    
    with open(os.path.join(DIR_WEB, 'style.css'), 'w', encoding='utf-8') as f:
        f.write(css)
    
    with open(os.path.join(DIR_WEB, 'script.js'), 'w', encoding='utf-8') as f:
        f.write(js)

if __name__ == "__main__":
    main()
