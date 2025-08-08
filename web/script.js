// Variáveis globais
let arquivosEncontrados = [];
let arquivoSelecionado = null;
let varreduraEmAndamento = false; // NOVO: controla estado do botão

// Elementos da UI
const spinnerOverlay = document.getElementById('spinnerOverlay');
const btnBuscar = document.getElementById('btn-buscar');
const tamanhoMinimo = document.getElementById('tamanho-minimo');
const sliderTamanhoMinimo = document.getElementById('slider-tamanho-minimo');
const sliderTamanhoLabel = document.getElementById('slider-tamanho-label');
const filesTableBody = document.getElementById('files-table-body');
const compressedFilesTable = document.getElementById('compressed-files-table');
const compactarDialog = document.getElementById('compactar-dialog');
const pastasLista = document.getElementById('pastas-lista');
const progressSection = document.getElementById('progress-section');
const progressBar = document.getElementById('progress-bar');
const logContent = document.getElementById('log-content');
const logContainer = document.getElementById('log-container');
const filesSection = document.getElementById('files-section');
const checkboxSelecionarTodos = document.getElementById('checkbox-selecionar-todos');
const filtroPastas = document.getElementById('filtro-pastas');
const compactarDestinoInput = document.getElementById('compactar-destino');
const destinoAtualSpan = document.getElementById('destino-atual');
const textoProgresso = document.getElementById('texto-progresso');
let pastaDestinoAtual = null;

// Sincronização slider/campo texto
sliderTamanhoMinimo.addEventListener('input', () => {
    tamanhoMinimo.value = sliderTamanhoMinimo.value;
    sliderTamanhoLabel.textContent = `${sliderTamanhoMinimo.value} MB`;
});
tamanhoMinimo.addEventListener('input', () => {
    sliderTamanhoMinimo.value = tamanhoMinimo.value;
    sliderTamanhoLabel.textContent = `${tamanhoMinimo.value} MB`;
});

// Carregar pastas ao abrir
document.addEventListener('DOMContentLoaded', async () => {
    sliderTamanhoLabel.textContent = `${sliderTamanhoMinimo.value} MB`;
    await carregarPastasDoSistema();
    await carregarArquivosCompactados();
});

// Chama backend para listar pastas
let todasPastas = []; // Guarda todas as pastas carregadas
async function carregarPastasDoSistema() {
    todasPastas = await eel.listar_pastas_sistema_js()();
    renderizarPastas(todasPastas);
}

function renderizarPastas(lista) {
    pastasLista.innerHTML = '';
    lista.forEach(pasta => {
        const tr = document.createElement('tr');
        const tdCheck = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true;
        checkbox.value = pasta;
        checkbox.className = 'checkbox-pasta';
        tdCheck.appendChild(checkbox);
        tr.appendChild(tdCheck);

        const tdNome = document.createElement('td');
        tdNome.textContent = pasta;
        tr.appendChild(tdNome);

        pastasLista.appendChild(tr);
    });

    // Atualiza o estado do "Selecionar todos" ao carregar
    checkboxSelecionarTodos.checked = true;
    sincronizarCheckboxSelecionarTodos();

    // Adiciona evento para cada checkbox individual
    document.querySelectorAll('.checkbox-pasta').forEach(cb => {
        cb.addEventListener('change', sincronizarCheckboxSelecionarTodos);
    });
}

// Filtro de pastas pelo nome a partir do 3º dígito
filtroPastas.addEventListener('input', () => {
    const filtro = filtroPastas.value.trim().toLowerCase();
    if (filtro.length < 3) {
        renderizarPastas(todasPastas);
    } else {
        const filtradas = todasPastas.filter(pasta =>
            pasta.toLowerCase().includes(filtro)
        );
        renderizarPastas(filtradas);
    }
});

// Checkbox "Selecionar todos"
checkboxSelecionarTodos.addEventListener('change', () => {
    const marcar = checkboxSelecionarTodos.checked;
    document.querySelectorAll('.checkbox-pasta').forEach(cb => {
        cb.checked = marcar;
    });
});

// Sincroniza o estado do "Selecionar todos" ao marcar/desmarcar individualmente
function sincronizarCheckboxSelecionarTodos() {
    const checkboxes = document.querySelectorAll('.checkbox-pasta');
    const todosMarcados = Array.from(checkboxes).every(cb => cb.checked);
    const nenhumMarcado = Array.from(checkboxes).every(cb => !cb.checked);
    checkboxSelecionarTodos.checked = todosMarcados;
    checkboxSelecionarTodos.indeterminate = !todosMarcados && !nenhumMarcado;
}

// Função utilitária para logar na interface (mantém cor, ícone, fonte, simplificado)
function logarUI(mensagem, tipo = 'info') {
    const logItem = document.createElement('div');
    let icone = '';
    switch (tipo) {
        case 'success': icone = '✅'; break;
        case 'error': icone = '❌'; break;
        case 'warning': icone = '⚠️'; break;
        default: icone = 'ℹ️';
    }
    logItem.className = `log-${tipo}`;
    logItem.innerHTML = `<span class="log-icon">${icone}</span><span>${mensagem}</span>`;
    logContent.appendChild(logItem);
    logContainer.scrollTop = logContainer.scrollHeight;
    eel.logando(`[FRONTEND] ${mensagem}`);
}

eel.expose(atualizar_progress_bar);

function atualizar_progress_bar(porcentagem, minutosRestantes=0) {
    const barra = document.getElementById("progresso-barra");
    if (barra) {
        barra.style.width = porcentagem + "%";
        barra.innerText = porcentagem + "%";
        textoProgresso.innerText = `Processando... ${minutosRestantes} min restantes - ${porcentagem}%`;
    }
}
// Função utilitária para mostrar notificações Bootstrap
function mostrarNotificacao(mensagem, tipo = 'info', tempo = 4000) {
    const container = document.getElementById('notificacao-container');
    if (!container) return; // Garante que o container existe
    const tipoBootstrap = {
        info: 'primary',
        success: 'success',
        error: 'danger',
        warning: 'warning'
    }[tipo] || 'primary';
    const id = 'toast-' + Date.now() + Math.floor(Math.random()*1000);
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${tipoBootstrap} border-0 show`;
    toast.id = id;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="d-flex  mb-2">
            <div class="toast-body">${mensagem}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove('show');
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 500);
    }, tempo);
}

// Exibe progresso/logs vindos do backend (apenas logs relevantes)
eel.expose(atualizar_progresso);
function atualizar_progresso(mensagem) {
    let tipo = 'info';
    let icone = 'ℹ️';
    let msg = mensagem;

    // Filtra logs para mostrar apenas os relevantes ao usuário
    if (
        mensagem.startsWith('Iniciando varredura nas pastas selecionadas') ||
        mensagem.startsWith('Varredura na pasta:') ||
        mensagem.startsWith('ENCONTRADO:') ||
        mensagem.startsWith('Ignorado') ||
        mensagem.startsWith('Varredura concluída') ||
        mensagem.startsWith('Varredura cancelada pelo usuário') ||
        mensagem.startsWith('Erro')
    ) {
        if (mensagem.includes('ENCONTRADO')) {
            tipo = 'success'; icone = '✅'; msg = mensagem.replace('ENCONTRADO:', 'Encontrado:');
        } else if (mensagem.includes('Erro')) {
            tipo = 'error'; icone = '❌'; msg = mensagem.replace('Erro', 'Erro');
        } else if (mensagem.includes('Ignorado')) {
            tipo = 'warning'; icone = '⚠️'; msg = mensagem.replace('Ignorado', 'Ignorado');
        } else if (mensagem.includes('cancelada')) {
            tipo = 'warning'; icone = '⚠️';
        }
        const logItem = document.createElement('div');
        logItem.className = `log-${tipo}`;
        logItem.innerHTML = `<span class="log-icon">${icone}</span><span>${msg}</span>`;
        logContent.appendChild(logItem);
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

// Exibe múltiplos logs vindos do backend (apenas relevantes)
eel.expose(atualizar_progresso_multiplo);
function atualizar_progresso_multiplo(mensagens) {
    mensagens.forEach(atualizar_progresso);
}

// Exibe barra de progresso
eel.expose(atualizar_barra_progresso);
function atualizar_barra_progresso(valor) {
    progressBar.style.display = 'block';
    progressBar.setAttribute('value', valor);
}

// Exibe arquivos encontrados
eel.expose(atualizar_lista_arquivos);
function atualizar_lista_arquivos(arquivos) {
    filesTableBody.innerHTML = '';
    arquivos.forEach(arquivo => {
        const tr = document.createElement('tr');
        const tdNome = document.createElement('td');
        const nomeCorrigido = arquivo.nome.replace(/[/\\]+[^/\\]+[/\\]/, '/');
        tdNome.textContent = nomeCorrigido;
        tr.appendChild(tdNome);

        const tdTamanho = document.createElement('td');
        tdTamanho.textContent = arquivo.tamanho_formatado;
        tr.appendChild(tdTamanho);

        const tdTipo = document.createElement('td');
        tdTipo.textContent = arquivo.tipo;
        tr.appendChild(tdTipo);

        const tdAcoes = document.createElement('td');
        // Único botão para compactar na mesma pasta
        const btnCompactarFopt = document.createElement('button');
        btnCompactarFopt.textContent = 'Compactar arquivo';
        btnCompactarFopt.className = 'botao-busca';
        btnCompactarFopt.style.backgroundColor = '#0078d4'; // Cor padrão principal
        btnCompactarFopt.addEventListener('click', () => {
            compactarArquivoFopt(arquivo.caminho, tr, arquivo);
        });
        tdAcoes.appendChild(btnCompactarFopt);

        tr.appendChild(tdAcoes);
        filesTableBody.appendChild(tr);
    });
    filesSection.style.display = 'block';
    // Restaura botão ao estado inicial ao encontrar arquivos
    btnBuscar.textContent = 'Iniciar Varredura de Arquivos';
    btnBuscar.classList.remove('cancelar');
    btnBuscar.disabled = false;
    varreduraEmAndamento = false;
}

// Função removida: Não compactamos mais arquivos em diretório diferente

// Compacta arquivo na mesma pasta com extensão .fopt
async function compactarArquivoFopt(caminho, tr, arquivo) {
    spinnerOverlay.style.display = 'flex';
    logarUI(`Compactando arquivo para formato .fopt: ${caminho}`, 'info');
    eel.compactar_arquivo_fopt_js(caminho);
}

// Callback do Python/Eel para compactação no mesmo diretório
eel.expose(_compactar_arquivo_fopt_callback);
function _compactar_arquivo_fopt_callback(resultado) {
    spinnerOverlay.style.display = 'none';
    if (resultado.sucesso) {
        logarUI(`Arquivo .fopt salvo em: ${resultado.destino}`, 'success');
        mostrarNotificacao('Arquivo .fopt criado com sucesso na mesma pasta!', 'success');
        carregarArquivosCompactados();
    } else {
        logarUI(`Erro: ${resultado.mensagem}`, 'error');
        mostrarNotificacao(resultado.mensagem, 'error');
    }
}

// Abre/descompacta arquivo
async function abrirArquivoDescompactado(destinoZip, nomeOriginal) {
    logarUI(`Solicitado abrir/descompactar: ${destinoZip} para ${nomeOriginal}`, 'info');
    const resultado = await eel.abrir_descompactar_arquivo_js(destinoZip, nomeOriginal)();
    if (resultado.sucesso) {
        logarUI(`Arquivo aberto/descompactado: ${resultado.mensagem}`, 'success');
        mostrarNotificacao(resultado.mensagem, 'success');
    } else {
        logarUI(`Erro ao abrir/descompactar: ${resultado.mensagem}`, 'error');
        mostrarNotificacao(resultado.mensagem, 'error');
    }
}

// Carrega arquivos compactados
async function carregarArquivosCompactados() {
    logarUI('Carregando lista de arquivos compactados...', 'info');
    compressedFilesTable.innerHTML = '';
    const dados = await eel.carregar_dados_js()();
    logarUI(`Dados recebidos: ${JSON.stringify(dados)}`, 'info');
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
    for (const [nomeZip, info] of Object.entries(dados)) {
        const tr = document.createElement('tr');
        const tdNome = document.createElement('td');
        tdNome.textContent = nomeZip;
        tr.appendChild(tdNome);
        const tdData = document.createElement('td');
        try {
            const data = new Date(info.data);
            tdData.textContent = data.toLocaleString();
        } catch {
            tdData.textContent = info.data || 'Data desconhecida';
        }
        tr.appendChild(tdData);
        const tdAcoes = document.createElement('td');
        const btnAbrir = document.createElement('button');
        btnAbrir.textContent = 'Abrir';
        btnAbrir.className = 'botao-busca';
        btnAbrir.addEventListener('click', () => {
            abrirArquivoDescompactado(info.compactado, info.original);
        });
        tdAcoes.appendChild(btnAbrir);
        tr.appendChild(tdAcoes);
        compressedFilesTable.appendChild(tr);
    }
}

// Exibe barra de progresso
eel.expose(atualizar_barra_progresso);
function atualizar_barra_progresso(valor) {
    progressBar.style.display = 'block';
    progressBar.setAttribute('value', valor);
}

// Finaliza varredura (atualiza UI e habilita botão)
eel.expose(finalizar_varredura);
function finalizar_varredura() {
    progressBar.setAttribute('value', '100');
    btnBuscar.textContent = 'Iniciar Varredura de Arquivos';
    btnBuscar.classList.remove('cancelar');
    btnBuscar.disabled = false;
    varreduraEmAndamento = false;
}

// Finaliza varredura cancelada (atualiza UI e habilita botão)
eel.expose(finalizar_varredura_cancelada);
function finalizar_varredura_cancelada() {
    btnBuscar.textContent = 'Iniciar Varredura de Arquivos';
    btnBuscar.classList.remove('cancelar');
    btnBuscar.disabled = false;
    varreduraEmAndamento = false;
}

// Garante que o botão nunca fique travado
btnBuscar.addEventListener('click', () => {
    // Se estiver em modo cancelar, cancela a varredura
    if (btnBuscar.classList.contains('cancelar')) {
        logarUI('Cancelando varredura...', 'warning');
        btnBuscar.textContent = 'Iniciar Varredura de Arquivos';
        btnBuscar.classList.remove('cancelar');
        btnBuscar.disabled = true;
        varreduraEmAndamento = false;
        eel.cancelar_varredura_js();
        return;
    }

    // Inicia varredura
    logarUI('Iniciando varredura de arquivos...', 'info');
    varreduraEmAndamento = true;
    btnBuscar.textContent = 'Cancelar Varredura';
    btnBuscar.classList.add('cancelar');
    btnBuscar.disabled = false;

    // Limpa logs e tabelas
    logContent.innerHTML = '';
    filesTableBody.innerHTML = '';
    progressSection.style.display = 'block';
    filesSection.style.display = 'none';
    progressBar.removeAttribute('value');

    // Obtém tamanho mínimo e pastas selecionadas
    const tamanhoMinimoValor = parseInt(sliderTamanhoMinimo.value) || 250;
    const selecionadas = [];
    document.querySelectorAll('#pastas-lista input[type="checkbox"]:checked').forEach(cb => {
        selecionadas.push(cb.value);
    });

    // Chama backend para iniciar varredura
    eel.varrer_arquivos_js(tamanhoMinimoValor, selecionadas);
});
