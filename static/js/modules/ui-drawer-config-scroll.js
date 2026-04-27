﻿var drawerAtivo = null;
function toggleDrawer(nome) {
  if (!nome || drawerAtivo === nome) {
    fecharDrawer();
  } else {
    abrirDrawer(nome);
  }
}
function abrirDrawer(nome) {
  fecharDrawer(false);
  drawerAtivo = nome;
  document.getElementById('drawerFixas').classList.toggle('open', nome === 'fixas');
  document.getElementById('drawerMetas').classList.toggle('open', nome === 'metas');
  document.getElementById('drawerOverlay').classList.add('show');
  document.getElementById('tabFixas').classList.toggle('ativo', nome === 'fixas');
  document.getElementById('tabMetas').classList.toggle('ativo', nome === 'metas');
}
function fecharDrawer(resetAtivo = true) {
  document.getElementById('drawerFixas').classList.remove('open');
  document.getElementById('drawerMetas').classList.remove('open');
  document.getElementById('drawerOverlay').classList.remove('show');
  document.getElementById('tabFixas').classList.remove('ativo');
  document.getElementById('tabMetas').classList.remove('ativo');
  if (resetAtivo) drawerAtivo = null;
}

var _cfgLinhas = parseInt(localStorage.getItem('cfgLinhas') || '15');
var _cfgTemaEscuro = localStorage.getItem('cfTemaEscuro') === 'true';
var _cfgDiaInicioMesFiscal = parseInt(localStorage.getItem('cfgDiaInicioMesFiscal') || '25');

// Aplica o tema na tag <html> imediatamente ao carregar o script para evitar tela piscando
if (_cfgTemaEscuro) document.documentElement.classList.add('dark-mode');

function abrirCfgApp() {
  document.getElementById('cfgLinhas').value = _cfgLinhas;
  document.getElementById('cfgDiaInicioMesFiscal').value = _cfgDiaInicioMesFiscal;
  const elTema = document.getElementById('cfgTema');
  if (elTema) elTema.checked = _cfgTemaEscuro;
  abrirModal('ovCfgApp');
}

function salvarCfgApp() {
  const v = parseInt(document.getElementById('cfgLinhas').value);
  if (!v || v < 1) return alert('Informe um número válido');
  _cfgLinhas = v;
  localStorage.setItem('cfgLinhas', v);
  
  const diaInicio = parseInt(document.getElementById('cfgDiaInicioMesFiscal').value);
  if (!diaInicio || diaInicio < 1 || diaInicio > 31) return alert('Dia de início do mês fiscal deve estar entre 1 e 31');
  _cfgDiaInicioMesFiscal = diaInicio;
  localStorage.setItem('cfgDiaInicioMesFiscal', diaInicio);
  
  const elTema = document.getElementById('cfgTema');
  if (elTema) {
    _cfgTemaEscuro = elTema.checked;
    localStorage.setItem('cfTemaEscuro', _cfgTemaEscuro ? 'true' : 'false');
    document.documentElement.classList.toggle('dark-mode', _cfgTemaEscuro);
  }

  // Salvar no backend
  fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({dia_inicio_mes_fiscal: diaInicio})
  }).catch(err => console.error('Erro ao salvar configuração:', err));

  fecharModal('ovCfgApp');
  
  // Recarregar dados para atualizar fixas aplicadas e mês fiscal
  if (typeof debouncedLoad === 'function') {
    debouncedLoad();
  } else if (typeof renderVisaoAtiva === 'function') {
    renderVisaoAtiva();
  } else {
    renderTabela();
  }
}

function resetarLargurasColunas() {
  if (!confirm('Resetar as larguras das colunas para o padrão?\n\nIsso irá remover todas as personalizações de largura.')) {
    return;
  }
  
  // Remover larguras salvas de todas as visões
  const viewName = (typeof viewAtiva !== 'undefined') ? viewAtiva : 'tabela';
  localStorage.removeItem('cf_widths_' + viewName);
  localStorage.removeItem('cf_widths_despesas');
  localStorage.removeItem('cf_widths_rendimentos');
  localStorage.removeItem('cf_widths_tabela');
  
  // Re-renderizar para aplicar larguras padrão
  if (typeof renderVisaoAtiva === 'function') {
    renderVisaoAtiva();
  } else if (typeof renderTabela === 'function') {
    renderTabela();
  }
  
  alert('Larguras das colunas resetadas com sucesso!');
}

window.CF_AplicarResize = function() {
  if (!document.getElementById('cf-grid-fix')) {
    const style = document.createElement('style');
    style.id = 'cf-grid-fix';
    style.innerHTML = `
      .main, .card { min-width: 0; max-width: 100%; }
      td.cat-nome { overflow: visible; }
      td.cat-nome:has(.dropdown-content.show) { z-index: 10; }
      .cc { display: flex; align-items: center; width: 100%; overflow: visible; box-sizing: border-box; }
      .cc > span:first-child { flex: 1 1 auto; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; margin-right: 4px; }
      .cc .fixas-badge, .cc .badge-conta { flex: 0 0 auto; margin-right: 4px; }
      .cc .cc-actions { flex: 0 0 auto; margin-left: auto; display: flex; align-items: center; }
    `;
    document.head.appendChild(style);
  }

  const tw = document.getElementById('tw');
  if (!tw) return;
  tw.style.overflowX = 'auto';
  const table = tw.querySelector('table');
  if (!table) return;

  let cg = table.querySelector('colgroup');
  if (!cg) {
    cg = document.createElement('colgroup');
    const ths = Array.from(table.querySelectorAll('thead th'));
    
    const viewName = (typeof viewAtiva !== 'undefined') ? viewAtiva : 'tabela';
    let savedWidths = [];
    try {
      savedWidths = JSON.parse(localStorage.getItem('cf_widths_' + viewName)) || [];
    } catch(e) {}
    
    let totalW = 0;
    ths.forEach((th, idx) => {
      const col = document.createElement('col');
      
      // Calcular largura real necessária baseada no conteúdo
      let w = savedWidths[idx];
      if (!w) {
        // Temporariamente remover table-layout:fixed para medir conteúdo real
        const originalLayout = table.style.tableLayout;
        table.style.tableLayout = 'auto';
        
        // Medir largura real do th (inclui padding, ícones, texto)
        const computedWidth = th.getBoundingClientRect().width;
        w = Math.max(computedWidth, 90); // Mínimo de 90px
        
        // Restaurar layout
        table.style.tableLayout = originalLayout;
      }
      
      col.style.width = w + 'px';
      cg.appendChild(col);
      totalW += w;
    });
    table.insertBefore(cg, table.firstChild);
    table.style.tableLayout = 'fixed';
    table.style.width = totalW + 'px';
    table.style.minWidth = '';
  }

  const ths = Array.from(table.querySelectorAll('thead th'));
  ths.forEach((th, idx) => {
    let handle = th.querySelector('.resize-handle');
    if (!handle) {
      handle = document.createElement('div');
      handle.className = 'resize-handle';
      th.appendChild(handle);
    }
    
    const newHandle = handle.cloneNode(true);
    handle.parentNode.replaceChild(newHandle, handle);
    
    newHandle.addEventListener('mousedown', function(e) {
      e.preventDefault();
      e.stopPropagation();
      const startX = e.pageX;
      const col = cg.children[idx];
      const startWidth = parseFloat(col.style.width) || th.offsetWidth;
      
      // Define um limite mínimo estático para permitir encolher a coluna livremente
      const minWidth = 60;
      
      newHandle.classList.add('resizing');
      
      function onMouseMove(evt) {
        const newWidth = Math.max(minWidth, startWidth + evt.pageX - startX);
        col.style.width = newWidth + 'px';
        
        let totalW = 0;
        Array.from(cg.children).forEach(c => totalW += parseFloat(c.style.width));
        table.style.width = totalW + 'px';
        
        const fixedTable = document.getElementById('tabelaFixed');
        if (fixedTable) {
           const fixedCg = fixedTable.querySelector('colgroup');
           if (fixedCg && fixedCg.children[idx]) fixedCg.children[idx].style.width = newWidth + 'px';
           fixedTable.style.width = totalW + 'px';
        }
      }
      function onMouseUp() {
        newHandle.classList.remove('resizing');
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        
        const currentWidths = [];
        Array.from(cg.children).forEach(c => currentWidths.push(parseFloat(c.style.width)));
        const viewName = (typeof viewAtiva !== 'undefined') ? viewAtiva : 'tabela';
        localStorage.setItem('cf_widths_' + viewName, JSON.stringify(currentWidths));
      }
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    });
  });
};

/**
 * Função Utilitária (DRY): Cria e retorna o validador da sombra de rolagem 
 * para qualquer contêiner da aplicação.
 * @param {HTMLElement} containerElement Contêiner que possui o scroll
 * @returns {Function} Função para atualizar a sombra (pode ser anexada a eventos de scroll)
 */
window.gerenciarSombraScrollNativa = function(containerElement) {
  if (!containerElement) return null;

  let shadow = containerElement.querySelector('.sticky-scroll-shadow');
  if (!shadow) {
    shadow = document.createElement('div');
    shadow.className = 'sticky-scroll-shadow';
    containerElement.appendChild(shadow);
  }

  const atualizarSombra = () => {
    const isAtBottom = containerElement.scrollHeight - containerElement.scrollTop <= containerElement.clientHeight + 10;
    if (!isAtBottom && containerElement.scrollHeight > containerElement.clientHeight) {
      shadow.classList.add('is-visible');
    } else {
      shadow.classList.remove('is-visible');
    }
  };

  return atualizarSombra;
};

function aplicarScrollDespesas() {
  const tw = document.getElementById('tw');
  if (!tw) return;
  const tabela = tw.querySelector('table');
  if (!tabela) return;

  const velhoWrap = document.getElementById('fixedWrap');
  if (velhoWrap) {
    if (tw._thObserver) {
      tw._thObserver.disconnect();
      delete tw._thObserver;
    }
    const tbFixed = document.getElementById('tbodyFixed');
    const tbOrig = tabela.querySelector('tbody');
    if (tbFixed && tbOrig) Array.from(tbFixed.rows).forEach(r => tbOrig.appendChild(r));
    velhoWrap.remove();
    tw.style.overflow = '';
    tabela.style.marginBottom = '';
    tw.removeAttribute('data-scroll');
  }

  if (tw._onScrollSync) {
    tw.removeEventListener('scroll', tw._onScrollSync);
    delete tw._onScrollSync;
  }

  const styleHide = document.getElementById('hide-scrollbar-style');
  if (styleHide) styleHide.remove();

  const tbody = tabela.querySelector('tbody');
  if (!tbody) return;
  const allRows = Array.from(tbody.rows);
  const firstFixed = allRows.findIndex(r =>
    r.classList.contains('tr-rec') ||
    r.classList.contains('tr-saldo') ||
    r.classList.contains('tr-mov') ||
    r.classList.contains('tr-conta') ||
    r.classList.contains('tr-total-contas') ||
    (r.querySelector('td .cc span') &&
     r.querySelector('td .cc span').textContent.trim().includes('Total Despesas'))
  );

  const nCatRows = allRows.filter(r => r.classList.contains('cat-row')).length;
  if (firstFixed <= 0 || nCatRows <= _cfgLinhas) {
    tw.style.maxHeight = '';
    tw.style.overflowY = '';
    const existingShadow = tw.querySelector('.sticky-scroll-shadow');
    if (existingShadow) existingShadow.remove();
    return;
  }

  const cgOrig = tabela.querySelector('colgroup');
  const widths = cgOrig ? Array.from(cgOrig.children).map(c => parseFloat(c.style.width)) : Array.from(tabela.querySelectorAll('thead th')).map(th => th.offsetWidth);

  const tabelaFixed = document.createElement('table');
  tabelaFixed.id = 'tabelaFixed';
  tabelaFixed.style.cssText = 'border-collapse:collapse;width:' + tabela.offsetWidth + 'px;table-layout:fixed;';
  const cg = document.createElement('colgroup');
  widths.forEach(w => {
    const col = document.createElement('col');
    col.style.width = w + 'px';
    cg.appendChild(col);
  });
  tabelaFixed.appendChild(cg);
  const tbFixed = document.createElement('tbody');
  tbFixed.id = 'tbodyFixed';
  allRows.slice(firstFixed).forEach(r => tbFixed.appendChild(r));
  tabelaFixed.appendChild(tbFixed);

  tw.style.overflowX = 'auto';
  const alturaMax = _cfgLinhas * 28 + 32;
  tw.style.maxHeight = alturaMax + 'px';
  tw.style.overflowY = 'auto';
  tw.setAttribute('data-scroll', '1');

  const wrapDiv = document.createElement('div');
  wrapDiv.id = 'fixedWrap';
  wrapDiv.style.overflowX = 'auto';
  wrapDiv.classList.add('hide-scrollbar');
  wrapDiv.appendChild(tabelaFixed);

  if (!document.getElementById('hide-scrollbar-style')) {
    const style = document.createElement('style');
    style.id = 'hide-scrollbar-style';
    style.innerHTML = `
      .hide-scrollbar::-webkit-scrollbar { display: none; }
      .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
    `;
    document.head.appendChild(style);
  }

  tw.parentNode.insertBefore(wrapDiv, tw.nextSibling);

  wrapDiv.scrollLeft = tw.scrollLeft;
  wrapDiv.addEventListener('scroll', function() {
    if (tw.scrollLeft !== wrapDiv.scrollLeft) tw.scrollLeft = wrapDiv.scrollLeft;
  });

  // Invocação DRY: Configura a sombra e guarda o validador
  const validarSombra = window.gerenciarSombraScrollNativa(tw);

  tw._onScrollSync = function() {
    const wrap = document.getElementById('fixedWrap');
    if (wrap && wrap.scrollLeft !== tw.scrollLeft) wrap.scrollLeft = tw.scrollLeft;

    // Executa a validação da sombra sem precisar injetar lógica hardcoded
    if (validarSombra) validarSombra();
  };
  tw.addEventListener('scroll', tw._onScrollSync);
  setTimeout(() => { if (tw._onScrollSync) tw._onScrollSync(); }, 50);
}

async function confirmarDelCategoria() {
  if (!renCtx) return;
  const catId = renCtx.id || renCtx;
  const nome = document.getElementById('renN').value || '(sem nome)';
  if (typeof window.excluirCategoriaMenu === 'function') window.excluirCategoriaMenu(catId, nome);
}

let _resizeTimer;
window.addEventListener('resize', function() {
  clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(function() {
    const tw = document.getElementById('tw');
    if (!tw) return;
    const fixedWrap = document.getElementById('fixedWrap');
    if (fixedWrap) {
      if (tw._thObserver) {
        tw._thObserver.disconnect();
        delete tw._thObserver;
      }
      const tbFixed = document.getElementById('tbodyFixed');
      const tabela = tw.querySelector('table');
      const tbOrig = tabela ? tabela.querySelector('tbody') : null;
      if (tbFixed && tbOrig) Array.from(tbFixed.rows).forEach(r => tbOrig.appendChild(r));
      fixedWrap.remove();
    }
    const tabela = tw.querySelector('table');
    if (tabela) {
      const cg = tabela.querySelector('colgroup');
      if (cg) cg.remove();
      tabela.style.tableLayout = '';
      tabela.style.width = '100%';
      tabela.style.minWidth = '';
    }
    tw.style.overflow = '';
    tw.style.maxHeight = '';
    tw.style.overflowY = '';
    if(window.CF_AplicarResize) window.CF_AplicarResize();
    aplicarScrollDespesas();
  }, 200);
});
