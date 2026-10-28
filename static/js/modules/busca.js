/* ========================================= */
/* MÓDULO DE BUSCA UNIFICADA (ANO ATIVO)     */
/* ========================================= */

var _buscaSeqId = 0;
var _buscaDebounceTimer = null;
var _ultimosResultadosBusca = [];
var _ultimoTermoBusca = '';

const BUSCA_BADGE_MAP = {
  despesa: { label: 'Despesa', cls: 'sb-despesa' },
  receita: { label: 'Receita', cls: 'sb-receita' },
  rendimento_lanc: { label: 'Rendimento', cls: 'sb-rendimento' },
  rendimento_local: { label: 'Local Rend.', cls: 'sb-rendimento' },
  deposito: { label: 'Conta', cls: 'sb-conta' },
  conta: { label: 'Conta', cls: 'sb-conta' },
  movimentacao: { label: 'Movimentação', cls: 'sb-mov' },
  fixa: { label: 'Fixa', cls: 'sb-fixa' },
  meta: { label: 'Meta', cls: 'sb-meta' },
  categoria: { label: 'Categoria', cls: 'sb-categoria' }
};

function normalizarSemAcento(str) {
  return String(str || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function destacarTermoHtml(texto, termo) {
  const raw = String(texto ?? '');
  if (!raw) return '';
  const escaped = window.escapeHtml ? window.escapeHtml(raw) : raw;
  const termoLimpo = String(termo || '').trim();
  if (!termoLimpo) {
    return window.formatBankIcons ? window.formatBankIcons(escaped) : escaped;
  }

  const normTexto = normalizarSemAcento(escaped);
  const normTermo = normalizarSemAcento(termoLimpo);
  if (!normTermo) {
    return window.formatBankIcons ? window.formatBankIcons(escaped) : escaped;
  }

  let idx = normTexto.indexOf(normTermo);
  if (idx === -1) {
    return window.formatBankIcons ? window.formatBankIcons(escaped) : escaped;
  }

  const antes = escaped.slice(0, idx);
  const meio = escaped.slice(idx, idx + normTermo.length);
  const depois = escaped.slice(idx + normTermo.length);
  const comMark = `${antes}<mark class="search-mark">${meio}</mark>${depois}`;
  return window.formatBankIcons ? window.formatBankIcons(comMark) : comMark;
}

function fecharDropdownBusca() {
  const dd = document.getElementById('dropdownBusca');
  if (dd) dd.style.display = 'none';
}

function limparBuscaAoMudarAno() {
  if (_buscaDebounceTimer) {
    clearTimeout(_buscaDebounceTimer);
    _buscaDebounceTimer = null;
  }
  _buscaSeqId++;
  _ultimosResultadosBusca = [];
  fecharDropdownBusca();
  const input = document.getElementById('inputBusca');
  const btnClear = document.getElementById('btnLimparBusca');
  if (input) input.value = '';
  if (btnClear) btnClear.style.display = 'none';
}
window.limparBuscaAoMudarAno = limparBuscaAoMudarAno;

async function executarBusca(termoForcado) {
  const input = document.getElementById('inputBusca');
  const dd = document.getElementById('dropdownBusca');
  if (!input || !dd) return;

  const termo = (termoForcado !== undefined ? termoForcado : input.value).trim();
  if (!termo) {
    fecharDropdownBusca();
    return;
  }

  const reqId = ++_buscaSeqId;
  _ultimoTermoBusca = termo;
  dd.innerHTML = '<div class="search-status">Buscando...</div>';
  dd.style.display = 'block';

  try {
    const r = await fetch(`/api/busca/${ano}?q=${encodeURIComponent(termo)}&_=${Date.now()}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });
    const data = await r.json();
    if (reqId !== _buscaSeqId) return;

    const resultados = (data && Array.isArray(data.resultados)) ? data.resultados : [];
    _ultimosResultadosBusca = resultados;
    renderDropdownBusca(resultados, termo);
  } catch (err) {
    if (reqId !== _buscaSeqId) return;
    dd.innerHTML = '<div class="search-status search-error">Erro ao buscar resultados.</div>';
    dd.style.display = 'block';
  }
}
window.executarBusca = executarBusca;

function renderDropdownBusca(resultados, termo) {
  const dd = document.getElementById('dropdownBusca');
  if (!dd) return;

  if (!resultados.length) {
    const termoSafe = window.escapeHtml ? window.escapeHtml(termo) : termo;
    dd.innerHTML = `<div class="search-status">Nenhum resultado para "<strong>${termoSafe}</strong>" em ${ano}.</div>`;
    dd.style.display = 'block';
    return;
  }

  const htmlItens = resultados.map((item, idx) => {
    const badgeInfo = BUSCA_BADGE_MAP[item.tipo] || { label: 'Item', cls: 'sb-default' };
    const mesTxt = item.mes && typeof MESES_ABREV !== 'undefined' && MESES_ABREV[item.mes - 1]
      ? `<span class="search-mes">${MESES_ABREV[item.mes - 1]}</span>`
      : '';
    const tituloHtml = destacarTermoHtml(item.titulo || '', termo);
    const subHtml = destacarTermoHtml(item.subtitulo || '', termo);
    let valorHtml = '';
    if (item.valor !== null && item.valor !== undefined) {
      const v = Number(item.valor) || 0;
      const vStr = (v < 0 ? '-' : '') + BRL(v);
      const clsVal = v < 0 ? 'neg' : 'pos';
      valorHtml = `<span class="search-val ${clsVal}">${vStr}</span>`;
    }

    return `<button type="button" class="search-item" data-idx="${idx}" onclick="selecionarResultadoBusca(${idx})">
      <div class="search-item-top">
        <span class="search-badge ${badgeInfo.cls}">${badgeInfo.label}</span>
        ${mesTxt}
        <span class="search-tit">${tituloHtml}</span>
        ${valorHtml}
      </div>
      ${subHtml ? `<div class="search-sub">${subHtml}</div>` : ''}
    </button>`;
  }).join('');

  dd.innerHTML = htmlItens;
  dd.style.display = 'block';
}

function limparDestaquesBusca() {
  document.querySelectorAll('.search-highlight-pulse, .search-item-highlight').forEach(el => {
    el.classList.remove('search-highlight-pulse', 'search-item-highlight');
  });
}

function rolarEDestacarElemento(el, classeDestaque, duracaoMs = 3500) {
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
  el.classList.remove(classeDestaque);
  // Força reflow para reiniciar animação CSS se clicado novamente
  void el.offsetWidth;
  el.classList.add(classeDestaque);
  setTimeout(() => {
    if (el) el.classList.remove(classeDestaque);
  }, duracaoMs);
}

function aguardarEDestacarItemModal(containerSelector, itemId) {
  if (itemId === null || itemId === undefined || itemId === '') return;
  let tentativas = 0;
  const maxTentativas = 25;
  const timer = setInterval(() => {
    tentativas++;
    const container = document.querySelector(containerSelector);
    if (container) {
      const row = container.querySelector(`.di[data-item-id="${itemId}"]`);
      if (row) {
        clearInterval(timer);
        rolarEDestacarElemento(row, 'search-item-highlight', 3500);
        return;
      }
    }
    if (tentativas >= maxTentativas) {
      clearInterval(timer);
    }
  }, 40);
}

function encontrarLinhaCategoria(catId, catNome) {
  if (catId !== null && catId !== undefined) {
    const byId = document.querySelector(`tr.cat-row[data-cat-id="${catId}"]`);
    if (byId) return byId;
  }
  if (!catNome) return null;
  const alvoNorm = String(catNome).trim().toLowerCase();
  const rows = Array.from(document.querySelectorAll('tr.cat-row'));
  return rows.find(r => {
    const span = r.querySelector('td.cat-nome .cc > span');
    const title = span ? (span.getAttribute('title') || span.textContent || '') : '';
    return title.trim().toLowerCase().startsWith(alvoNorm);
  }) || null;
}

async function selecionarResultadoBusca(idx) {
  const item = _ultimosResultadosBusca[idx];
  if (!item) return;

  fecharDropdownBusca();
  limparDestaquesBusca();

  if (item.visao === 'drawer_fixas') {
    if (typeof abrirDrawer === 'function') abrirDrawer('fixas');
    setTimeout(() => {
      const el = document.getElementById(`fxli-${item.id}`);
      rolarEDestacarElemento(el, 'search-item-highlight', 3500);
    }, 80);
    return;
  }

  if (item.visao === 'drawer_metas') {
    if (typeof abrirDrawer === 'function') abrirDrawer('metas');
    setTimeout(() => {
      const el = document.getElementById(`mli-${item.id}`);
      rolarEDestacarElemento(el, 'search-item-highlight', 3500);
    }, 80);
    return;
  }

  if (item.visao === 'rendimentos') {
    if (typeof viewAtiva !== 'undefined' && viewAtiva !== 'rendimentos') {
      await setView('rendimentos', false);
    }
    const tr = document.querySelector(`tr.cat-row[data-local-id="${item.local_id}"]`);
    const td = (tr && item.mes) ? tr.querySelector(`td[data-mes="${item.mes}"]`) : null;
    rolarEDestacarElemento(td || tr, 'search-highlight-pulse', 3500);

    if (item.tipo === 'rendimento_lanc' && item.mes && typeof abrirRendimentoLanc === 'function') {
      await abrirRendimentoLanc(item.local_id, item.local_nome || item.titulo, item.mes);
      aguardarEDestacarItemModal('#rendLancLista', item.id);
    }
    return;
  }

  // Visão de Despesas
  if (typeof viewAtiva !== 'undefined' && viewAtiva !== 'despesas') {
    await setView('despesas', false);
  }

  let tr = null;
  if (item.tipo === 'despesa' || item.tipo === 'categoria') {
    tr = encontrarLinhaCategoria(item.cat_id, item.categoria);
  } else if (item.tipo === 'receita') {
    tr = document.querySelector('tr.tr-rec');
  } else if (item.tipo === 'movimentacao') {
    tr = document.querySelector('tr.tr-mov');
  } else if (item.tipo === 'deposito' || item.tipo === 'conta') {
    tr = document.querySelector(`tr.tr-conta[data-conta-id="${item.conta_id}"]`);
  }

  const td = (tr && item.mes) ? tr.querySelector(`td[data-mes="${item.mes}"]`) : null;
  rolarEDestacarElemento(td || tr, 'search-highlight-pulse', 3500);

  if (item.tipo === 'despesa' && item.mes && typeof abrirDet === 'function') {
    const titModal = `${item.categoria} - ${MESES[item.mes - 1]}`;
    abrirDet(item.mes, item.categoria, titModal);
    aguardarEDestacarItemModal('#detL', item.id);
  } else if (item.tipo === 'receita' && item.mes && typeof verRec === 'function') {
    verRec(item.mes);
    aguardarEDestacarItemModal('#detL', item.id);
  } else if (item.tipo === 'deposito' && item.mes && typeof abrirDep === 'function') {
    abrirDep(item.conta_id, item.conta_nome || item.titulo, item.mes);
    aguardarEDestacarItemModal('#depL', item.id);
  } else if (item.tipo === 'movimentacao' && item.mes && typeof abrirMov === 'function') {
    abrirMov(item.mes);
    aguardarEDestacarItemModal('#movL', item.id);
  }
}
window.selecionarResultadoBusca = selecionarResultadoBusca;

(function initBuscaListeners() {
  const input = document.getElementById('inputBusca');
  const btnSearch = document.getElementById('btnExecutarBusca');
  const btnClear = document.getElementById('btnLimparBusca');
  const searchBox = document.getElementById('searchBox');

  if (input) {
    input.addEventListener('input', function() {
      const val = input.value;
      const trimmed = val.trim();
      if (btnClear) {
        btnClear.style.display = val.length > 0 ? 'inline-flex' : 'none';
      }
      if (_buscaDebounceTimer) {
        clearTimeout(_buscaDebounceTimer);
        _buscaDebounceTimer = null;
      }
      if (!trimmed) {
        _buscaSeqId++;
        fecharDropdownBusca();
        return;
      }
      // Mais de 5 caracteres: pesquisa automática ao digitar
      if (trimmed.length > 5) {
        _buscaDebounceTimer = setTimeout(() => {
          executarBusca(trimmed);
        }, 250);
      } else {
        // 5 ou menos caracteres: fecha resultados antigos e aguarda clique na lupa
        fecharDropdownBusca();
      }
    });

    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        e.stopPropagation();
        if (_buscaDebounceTimer) {
          clearTimeout(_buscaDebounceTimer);
          _buscaDebounceTimer = null;
        }
        const trimmed = input.value.trim();
        if (trimmed.length > 0) {
          executarBusca(trimmed);
        }
      } else if (e.key === 'Escape') {
        fecharDropdownBusca();
        input.blur();
      }
    });

    input.addEventListener('focus', function() {
      const trimmed = input.value.trim();
      if (trimmed && _ultimosResultadosBusca.length > 0 && trimmed === _ultimoTermoBusca) {
        const dd = document.getElementById('dropdownBusca');
        if (dd && dd.innerHTML.trim() !== '') dd.style.display = 'block';
      }
    });
  }

  if (btnSearch) {
    btnSearch.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      if (_buscaDebounceTimer) {
        clearTimeout(_buscaDebounceTimer);
        _buscaDebounceTimer = null;
      }
      if (!input) return;
      const trimmed = input.value.trim();
      if (trimmed.length > 0) {
        executarBusca(trimmed);
      } else {
        input.focus();
      }
    });
  }

  if (btnClear) {
    btnClear.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      if (_buscaDebounceTimer) {
        clearTimeout(_buscaDebounceTimer);
        _buscaDebounceTimer = null;
      }
      _buscaSeqId++;
      _ultimosResultadosBusca = [];
      _ultimoTermoBusca = '';
      fecharDropdownBusca();
      if (input) {
        input.value = '';
        input.focus();
      }
      btnClear.style.display = 'none';
    });
  }

  document.addEventListener('click', function(e) {
    if (searchBox && !searchBox.contains(e.target)) {
      fecharDropdownBusca();
    }
  });
})();
