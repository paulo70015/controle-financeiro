var __boot = window.CF_BOOT || {};
var ano = Number(__boot.ano || new Date().getFullYear()), dados = {};
const MESES = __boot.meses || ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
const MESES_ABREV = __boot.meses_abrev || ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const anos_srv = __boot.anos || [];
var viewAtiva = sessionStorage.getItem('cfViewAtiva') === 'rendimentos' ? 'rendimentos' : 'despesas';
var isAnoBloqueado = false;
// Inicializa dia de início do mês fiscal via localStorage; load() sobrescreve se o servidor retornar config
var _cfgDiaInicioMesFiscal = Number(localStorage.getItem('cfgDiaInicioMesFiscal')) || 25;

function parseVal(s) {
  if (s === null || s === undefined) return null;
  s = String(s).trim();
  if (s === '' || s === '--' || s === '-') return null;
  const neg = s.startsWith('-');
  let d = s.replace(/[^\d,.]/g, '');
  if (!d) return null;

  const lastComma = d.lastIndexOf(',');
  const lastDot = d.lastIndexOf('.');

  if (lastComma > -1 && lastDot > -1) {
    // Ambos presentes: o que vier por último é o separador decimal
    if (lastComma > lastDot) {
      d = d.replace(/\./g, '').replace(',', '.');
    } else {
      d = d.replace(/,/g, '');
    }
  } else if (lastComma > -1) {
    // Só vírgula: vírgula é decimal (ex: 12,50 ou 1500,00)
    const parts = d.split(',');
    const dec = parts.pop();
    d = parts.join('') + '.' + dec;
  } else if (lastDot > -1) {
    const dots = d.split('.').length - 1;
    if (dots > 1) {
      // Múltiplos pontos: primeiro(s) são milhar, último é decimal (ex: 1.500.00 → 1500.00)
      const parts = d.split('.');
      const dec = parts.pop();
      d = parts.join('') + '.' + dec;
    } else {
      // Um único ponto: milhar se após o ponto houver exatamente 3 dígitos (ex: 1.500)
      const afterDot = d.slice(lastDot + 1);
      if (afterDot.length === 3) {
        d = d.replace(/\./g, '');
      }
      // Caso contrário mantém como decimal (ex: 12.50)
    }
  }

  const v = parseFloat(d);
  if (isNaN(v)) return null;
  return neg ? -v : v;
}
const BRL = v => 'R$ ' + Math.abs(v).toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});

function focarCampo(id, delay = 50) {
  setTimeout(() => { const el = document.getElementById(id); if (el) { el.focus(); el.select(); } }, delay);
}

function formatarDataHoraBR(dataString) {
  if (!dataString) return '';
  const dt = new Date(dataString.replace(' ', 'T') + 'Z');
  return `${dt.toLocaleDateString('pt-BR')} às ${dt.toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'})}`;
}

async function safeApiCall(url, options = {}, defaultError = 'Erro na operação') {
  // Garantir que mutações não sejam servidas do cache do navegador
  const mergedOptions = {
    ...options,
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      ...(options.headers || {}),
    },
  };
  const response = await fetch(url, mergedOptions);
  if (!response.ok) {
    const err = await response.json().catch(() => ({ erro: 'Erro de comunicação com o servidor.' }));
    throw new Error(err.erro || defaultError);
  }
  return response;
}

function fecharModal(id) { 
  document.getElementById(id).classList.remove('show'); 
  if (id === 'ovD' && document.getElementById('dIgnorar')) document.getElementById('dIgnorar').checked = false;
  if (id === 'ovDet' && document.getElementById('detIgnorar')) document.getElementById('detIgnorar').checked = false;
}
function abrirModal(id) { 
  document.getElementById(id).classList.add('show'); 
}
document.querySelectorAll('.ov').forEach(o => o.addEventListener('click', e => {
  if (e.target !== o) return;
  if (o.id === 'ovDet') { fecharEefetivarDet(); return; }
  if (o.id === 'ovDep') { fecharEefetivarDep(); return; }
  fecharModal(o.id);
}));

async function mudarAno(event, novoAno) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const numNovoAno = Number(novoAno);
  if (numNovoAno === Number(ano)) return false; // Cláusula de guarda rigorosa

  ano = numNovoAno;
  // Atualiza a URL na barra de endereços silenciosamente
  window.history.pushState({ ano: numNovoAno }, '', '?ano=' + numNovoAno);
  
  // Feedback visual imediato para evitar a percepção de lentidão
  document.body.style.cursor = 'wait';
  document.querySelectorAll('#anoTabs a').forEach(a => {
    a.classList.remove('ativo');
    if (a.getAttribute('href') === '?ano=' + numNovoAno) {
      a.classList.add('ativo');
    }
  });

  // Pulo do gato: Força o navegador a desenhar (paint) o feedback visual ANTES
  // de travar a thread principal com o fetch e a renderização pesada
  await new Promise(resolve => setTimeout(resolve, 15));

  try {
    await load(true);
  } finally {
    document.body.style.cursor = 'default';
  }
  return false;
}

let currentLoadId = 0;
let loadDebounceTimer = null;
let loadDebounceResolvers = [];

function debouncedLoad(showLoader = false) {
  return new Promise(resolve => {
    loadDebounceResolvers.push(resolve);
    if (loadDebounceTimer) clearTimeout(loadDebounceTimer);
    loadDebounceTimer = setTimeout(async () => {
      loadDebounceTimer = null;
      const resolvers = loadDebounceResolvers.splice(0);
      await load(showLoader);
      resolvers.forEach(r => r());
    }, 50);
  });
}

async function load(showLoader = false) {
  const myLoadId = ++currentLoadId;
  const tw = document.getElementById('tw');
  if (showLoader && tw) {
    tw.style.opacity = '0.5';
    tw.style.pointerEvents = 'none';

    // Garante que a opacidade seja renderizada na tela antes do bloqueio da thread
    await new Promise(resolve => setTimeout(resolve, 15));
  }

  try {
  // Limpar cache de tooltips ao recarregar dados
  if (typeof limparCacheTooltip === 'function') limparCacheTooltip();
  
  const r = await fetch('/api/dados/' + ano + '?_=' + Date.now(), {
    cache: 'no-store',
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    }
  });
  const novosDados = await r.json();

  // Evita Race Condition: descarta dados velhos se um clique mais novo já ocorreu
  if (myLoadId !== currentLoadId) return;

  dados = novosDados;

  // Sincroniza a lista de anos com o servidor (fonte da verdade: tabela `anos`)
  if (novosDados.anos && Array.isArray(novosDados.anos) && novosDados.anos.length > 0) {
    anos_srv.length = 0;
    anos_srv.push(...novosDados.anos);
  }

  isAnoBloqueado = !!dados.is_bloqueado;
  document.body.classList.toggle('ano-bloqueado', isAnoBloqueado);
  
  // Atualizar configuração de dia de início do mês fiscal
  if (dados.config && dados.config.dia_inicio_mes_fiscal) {
    _cfgDiaInicioMesFiscal = parseInt(dados.config.dia_inicio_mes_fiscal) || 25;
    localStorage.setItem('cfgDiaInicioMesFiscal', _cfgDiaInicioMesFiscal);
  }

  Object.values(dados.despesas || {}).forEach(cat => {
    Object.keys(cat).forEach(m => {
      if (cat[m] && cat[m].valor !== undefined) cat[m].valor = parseFloat(cat[m].valor) || 0;
    });
  });
  Object.keys(dados.receitas || {}).forEach(m => { dados.receitas[m] = parseFloat(dados.receitas[m]) || 0; });
  const anosExtras = JSON.parse(sessionStorage.getItem('anosExtras') || '[]');
  const todosAnos = [...new Set([...anos_srv, ...anosExtras])].sort((a, b) => b - a);
  
  const htmlTabs = todosAnos.map(a => {
    const isCurrent = Number(a) === Number(ano);
    // Oculta o botão X no ano atual e garante exibição nos outros mesmo em estado de bloqueio
    const btnExcluir = isCurrent ? '' : `<button class="ano-del" style="display: inline-block !important; opacity: 1 !important; pointer-events: auto !important;" onclick="removerAno(event,${a})" title="Remover ano ${a}">✕</button>`;
    return `<a href="?ano=${a}" onclick="mudarAno(event, ${a}); return false;" class="${isCurrent ? 'ativo' : ''}">${a}${btnExcluir}</a>`;
  }).join('');
  
  document.getElementById('anoTabs').innerHTML = htmlTabs;
  renderVisaoAtiva();
  renderFixas();
  renderMetas();
  popularSel();
  if (typeof checkUndoCsvButton === 'function') {
    checkUndoCsvButton();
  }
  } finally {
    // Só remove a opacidade se esta for a requisição mais recente e válida
    if (showLoader && tw && myLoadId === currentLoadId) {
      tw.style.opacity = '1';
      tw.style.pointerEvents = 'auto';
    }
  }
}

function executarComScrollSalvo(callback) {
  const tw = document.getElementById('tw');
  const savedScrollTop = tw ? tw.scrollTop : 0;
  const savedScrollLeft = tw ? tw.scrollLeft : 0;
  const savedWindowScrollY = window.scrollY;

  // Evita que a tela "pule" para cima ao recriar o DOM
  document.body.style.minHeight = document.body.offsetHeight + 'px';

  callback();

  if (tw) {
    tw.scrollTop = savedScrollTop;
    tw.scrollLeft = savedScrollLeft;
  }
  window.scrollTo(window.scrollX, savedWindowScrollY);
  document.body.style.minHeight = '';
}

function renderVisaoAtiva() {
  executarComScrollSalvo(() => {
    limparArtefatosTabelaDespesas();
    const tw = document.getElementById('tw');
    if (tw) tw.innerHTML = '';
    atualizarAbasVisao();
    if (viewAtiva === 'rendimentos') {
      try {
        renderRendimentos();
      } finally {
        sanitizarQuadroDespesasEmRendimentos();
        setTimeout(sanitizarQuadroDespesasEmRendimentos, 0);
      }
    } else {
      renderTabela();
    }
  });
}

function atualizarAbasVisao() {
  const tabDesp = document.getElementById('viewTabDespesas');
  const tabRend = document.getElementById('viewTabRendimentos');
  const acoesDesp = document.getElementById('acoesDespesas');
  const acoesRend = document.getElementById('acoesRendimentos');
  if (!tabDesp || !tabRend) return;
  tabDesp.textContent = 'Despesas ' + ano;
  tabRend.textContent = 'Rendimentos ' + ano;
  tabDesp.classList.toggle('ativo', viewAtiva === 'despesas');
  tabRend.classList.toggle('ativo', viewAtiva === 'rendimentos');
  if (acoesDesp) acoesDesp.style.display = viewAtiva === 'despesas' ? 'flex' : 'none';
  if (acoesRend) acoesRend.style.display = viewAtiva === 'rendimentos' ? 'flex' : 'none';

  let btnLock = document.getElementById('btnTravarAno');
  if (!btnLock) {
    btnLock = document.createElement('button');
    btnLock.id = 'btnTravarAno';
    // Removido o "bs" (small) e hacks de altura para igualar o tamanho natural das abas
    btnLock.className = 'btn';
    btnLock.style.marginLeft = '16px';
    btnLock.style.fontWeight = 'bold';
    btnLock.style.borderRadius = '16px'; // Mantém o visual de "pílula"
    tabRend.parentNode.insertBefore(btnLock, tabRend.nextSibling);
  }
  btnLock.onclick = (e) => toggleTravarAno(e, ano);
  btnLock.title = isAnoBloqueado ? 'Ano travado. Clique para desbloquear.' : 'Ano aberto. Clique para travar.';
  btnLock.innerHTML = isAnoBloqueado ? '&#9679; TRAVADO' : '&#9675; ABERTO';
  
  // Agora o JS apenas gerencia os estados (classes), deixando as cores para o CSS!
  btnLock.className = isAnoBloqueado ? 'btn btn-travado' : 'btn btn-aberto';
}

async function setView(view, showLoader = true) {
  viewAtiva = view === 'rendimentos' ? 'rendimentos' : 'despesas';
  sessionStorage.setItem('cfViewAtiva', viewAtiva);
  
  const tw = document.getElementById('tw');
  if (showLoader && tw) {
    tw.style.opacity = '0.5';
    tw.style.pointerEvents = 'none';
    await new Promise(resolve => setTimeout(resolve, 15));
  }
  try {
    renderVisaoAtiva();
  } finally {
    if (showLoader && tw) {
      tw.style.opacity = '1';
      tw.style.pointerEvents = 'auto';
    }
  }
}

function sanitizarQuadroDespesasEmRendimentos() {
  if (viewAtiva !== 'rendimentos') return;
  const tw = document.getElementById('tw');
  if (!tw) return;
  const fixedWrap = document.getElementById('fixedWrap');
  if (fixedWrap) fixedWrap.remove();
  const tabelaFixed = document.getElementById('tabelaFixed');
  if (tabelaFixed) tabelaFixed.remove();
  const linhasFixasDespesas = tw.querySelectorAll(
    'tr.tr-rec, tr.tr-mov, tr.tr-saldo, tr.tr-conta, tr.tr-total-contas'
  );
  linhasFixasDespesas.forEach(l => l.remove());
  Array.from(tw.querySelectorAll('tbody tr')).forEach(tr => {
    const primeira = tr.querySelector('td.cat-nome span');
    if (!primeira) return;
    const txt = (primeira.textContent || '').toLowerCase().trim();
    if (txt.includes('total despesas')) tr.remove();
  });
}

function limparArtefatosTabelaDespesas() {
  const tw = document.getElementById('tw');
  if (!tw) return;
  const fixedWrap = document.getElementById('fixedWrap');
  if (fixedWrap) fixedWrap.remove();
  const tabelaFixed = document.getElementById('tabelaFixed');
  if (tabelaFixed) tabelaFixed.remove();
  tw.style.maxHeight = '';
  tw.style.overflowY = '';
  tw.style.overflowX = '';
  tw.removeAttribute('data-scroll');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    if (document.activeElement && document.activeElement.tagName === 'TEXTAREA') return;
    if (document.activeElement && document.activeElement.tagName === 'BUTTON') return;
    
    if (document.activeElement && document.activeElement.classList.contains('inline-edit-input')) {
      e.preventDefault();
      const parentBox = document.activeElement.closest('.inline-edit-box');
      if (parentBox) {
        const btnSalvar = parentBox.querySelector('.bv.inline-edit-btn');
        if (btnSalvar) btnSalvar.click();
      }
      return;
    }

    const modalAberto = document.querySelector('.ov.show');
    if (modalAberto) {
      e.preventDefault();
      switch (modalAberto.id) {
        case 'ovD': return typeof salvarD === 'function' && salvarD();
        case 'ovR': return typeof salvarR === 'function' && salvarR();
        case 'ovLote': return typeof salvarLote === 'function' && salvarLote();
        case 'ovConta': return typeof salvarConta === 'function' && salvarConta();
        case 'ovEditConta': return typeof salvarEditConta === 'function' && salvarEditConta();
        case 'ovMov': return typeof salvarMov === 'function' && salvarMov();
        case 'ovRen': return typeof confirmarRen === 'function' && confirmarRen();
        case 'ovC': return typeof salvarC === 'function' && salvarC();
        case 'ovAno': return typeof confirmarNovoAno === 'function' && confirmarNovoAno();
        case 'ovCfgApp': return typeof salvarCfgApp === 'function' && salvarCfgApp();
        case 'ovRendAdd': return typeof salvarRendimentoAdd === 'function' && salvarRendimentoAdd();
        case 'ovRendLocal': return typeof salvarRendimentoLocal === 'function' && salvarRendimentoLocal();
        case 'ovRendProj': return typeof salvarRendimentoProjecao === 'function' && salvarRendimentoProjecao();
        case 'ovDep': return typeof salvarDepositoEFechar === 'function' && salvarDepositoEFechar();
        case 'ovDet': return typeof addLancEFechar === 'function' && addLancEFechar();
        case 'ovRendLanc': return typeof salvarRendimentoLancamentoEFechar === 'function' && salvarRendimentoLancamentoEFechar();
      }
    }
  }
});

// Ouve os botões de Voltar/Avançar do navegador para trocar o ano corretamente
window.addEventListener('popstate', async function(e) {
  const params = new URLSearchParams(window.location.search);
  const urlAno = parseInt(params.get('ano')) || Number(__boot.ano || new Date().getFullYear());
  if (urlAno !== ano) {
    ano = urlAno;
    await load(true);
  }
});

load(true);
