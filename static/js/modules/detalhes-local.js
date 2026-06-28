﻿﻿﻿﻿var detCtx = {};
var editandoId = null;
var editandoTipo = null;
var depEditandoId = null;
var detOriginalData = null;
var depOriginalData = null;
var detDeleteQueue = [];
var depDeleteQueue = [];

const detUndoManager = new UndoManager('detBtnUndo', { get queue() { return detDeleteQueue; }, set queue(v) { detDeleteQueue = v; } });
const depUndoManager = new UndoManager('depBtnUndo', { get queue() { return depDeleteQueue; }, set queue(v) { depDeleteQueue = v; } });

function preencherMesesEdicaoDet() {
  const select = document.getElementById('detMesEditar');
  if (!select) return;
  select.innerHTML = MESES.map((mesNome, index) => `<option value="${index + 1}">${mesNome}</option>`).join('');
}

function toggleMesEdicaoDet(isEdit) {
  const container = document.getElementById('detMesContainer');
  const select = document.getElementById('detMesEditar');
  if (!container || !select) return;
  container.style.display = isEdit ? 'block' : 'none';
  select.disabled = !isEdit;
  if (!isEdit) select.value = String(detCtx.mes || 1);
}

function toggleEditUiDet(isEdit, isDep = false) {
  const b1 = document.querySelector(isDep ? 'button[onclick="salvarDeposito()"]' : 'button[onclick="addLanc()"]');
  const b2 = document.querySelector(isDep ? 'button[onclick="salvarDepositoEFechar()"]' : 'button[onclick="addLancEFechar()"]');
  if (b1) b1.textContent = isEdit ? 'Alterar' : '+ Lançar';
  if (b2) b2.textContent = isEdit ? 'Alterar e fechar' : 'Salvar e fechar';
  if (!isDep) toggleMesEdicaoDet(isEdit);
}

window.editarDet = function(id, tipo, valor, nota, ignorar = false, notaOriginal = '') {
  window.iniciarEdicaoInline({
    checkLock: true,
    onInit: () => {
      editandoId = id;
      editandoTipo = tipo;
      detOriginalData = tipo === 'receita'
        ? { valor, nota: notaOriginal || '', ignorar_total: false, descricao: nota || 'Receita' }
        : { valor, nota, ignorar_total: ignorar, descricao: nota };
    },
    campos: [
      { id: 'aV', valor: valor, formatar: v => (v !== undefined && v !== null && v !== '') ? parseFloat(v).toLocaleString('pt-BR', {minimumFractionDigits:2}) : '' },
      { id: 'aN', valor: nota },
      { id: 'detIgnorar', valor: ignorar, type: 'checkbox' },
      { id: 'detMesEditar', valor: detCtx.mes }
    ],
    toggleFn: isEdit => toggleEditUiDet(isEdit, false),
    focusId: 'aV'
  });
};

window.editarDep = function(id, valor, nota) {
  window.iniciarEdicaoInline({
    checkLock: false, // Mantendo o comportamento original que não bloqueia depósitos da conta
    onInit: () => {
      depEditandoId = id;
      depOriginalData = { valor, nota };
    },
    campos: [
      { id: 'depV', valor: valor, formatar: v => (v !== undefined && v !== null && v !== '') ? parseFloat(v).toLocaleString('pt-BR', {minimumFractionDigits:2}) : '' },
      { id: 'depN', valor: nota }
    ],
    toggleFn: isEdit => toggleEditUiDet(isEdit, true),
    focusId: 'depV'
  });
};

async function executarLancamentoDet() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) {
    alert('Este ano está travado. Desbloqueie primeiro para alterar.');
    return false;
  }
  const v = parseVal(document.getElementById('aV').value);
  const n = document.getElementById('aN').value;
  const mesEditado = document.getElementById('detMesEditar');
  const mesDestino = mesEditado ? parseInt(mesEditado.value, 10) : detCtx.mes;
  if (v === null && !n) return false;
  if (typeof hideUndoCsvButton === 'function') hideUndoCsvButton();
  
  if (detCtx.cat === '__rec__') {
    const isEdit = editandoId && editandoTipo === 'receita';
    const url = isEdit ? '/api/receita/' + editandoId : '/api/receita';
    const method = isEdit ? 'PUT' : 'POST';
    const body = isEdit 
        ? {descricao: n || 'Receita', valor: v||0, nota: detOriginalData.nota || '', mes: mesDestino}
        : {ano, mes: detCtx.mes, descricao: n || 'Receita', valor: v||0, nota: ''};
    
    await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    if (isEdit) {
      detUndoManager.push({ type: 'edit', url, oldBody: {descricao: detOriginalData.descricao || 'Receita', valor: detOriginalData.valor || 0, nota: detOriginalData.nota || '', mes: detCtx.mes} });
    }
  } else {
    const ign = document.getElementById('detIgnorar') ? document.getElementById('detIgnorar').checked : false;
    const isEdit = editandoId && editandoTipo === 'despesa';
    const url = isEdit ? '/api/despesa/' + editandoId : '/api/despesa';
    const method = isEdit ? 'PUT' : 'POST';
    const body = isEdit
        ? {valor: v||0, nota: n, ignorar_total: ign, mes: mesDestino}
        : {ano, mes: detCtx.mes, categoria: detCtx.cat, valor: v||0, nota: n, ignorar_total: ign};
        
    await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    if (isEdit) {
      detUndoManager.push({ type: 'edit', url, oldBody: {valor: detOriginalData.valor || 0, nota: detOriginalData.nota || '', ignorar_total: !!detOriginalData.ignorar_total, mes: detCtx.mes} });
    }
  }
  editandoId = null;
  editandoTipo = null;
  toggleEditUiDet(false, false);
  return true;
}

async function addLancEFechar() {
  await executarLancamentoDet();
  await flushDeleteQueue(detDeleteQueue, item => item.tipo === 'receita' ? '/api/receita/' + item.id : '/api/despesa/' + item.id);
  detDeleteQueue = [];
  detUndoManager.clear();
  fecharModal('ovDet');
  await debouncedLoad();
}

async function carregarDetLocal() {
  const cat = detCtx.cat;
  const mes = detCtx.mes;
  const el = document.getElementById('detL');
  const idsRemovidos = detDeleteQueue.map(x => x.id);
  const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
  
  if (cat === '__rec__') {
    const r = await fetch(`/api/receitas/${ano}/${mes}?_=${Date.now()}`);
    const rows = await r.json();
    const visiveis = rows.filter(r => !idsRemovidos.includes(r.id));
    
    const total = visiveis.reduce((s, r) => s + (r.valor || 0), 0);
    const tituloFormatado = window.formatBankIcons ? window.formatBankIcons(detCtx.tit || '') : (detCtx.tit || '');
    document.getElementById('detT').innerHTML = `${tituloFormatado} <span style="font-size:13px; font-weight:bold; color:var(--txt-st2); background:var(--bg-st2); padding:3px 8px; border-radius:12px; margin-left:6px; vertical-align:middle">${BRL(total)}</span>`;

    if (!visiveis.length) { el.innerHTML = '<p class="empty-state">Nenhuma receita.</p>'; return; }
    
    el.innerHTML = visiveis.map(r => {
      const descricaoEscaped = window.escapeJsSingleQuoted ? window.escapeJsSingleQuoted(r.descricao || 'Receita') : (r.descricao || 'Receita').replace(/'/g, "\\'");
      const notaEscaped = window.escapeJsSingleQuoted ? window.escapeJsSingleQuoted(r.nota || '') : (r.nota || '').replace(/'/g, "\\'");
      let notaFormatada = r.descricao + (r.nota ? ` (${r.nota})` : '');
      if (window.formatBankIcons) notaFormatada = window.formatBankIcons(notaFormatada);
      return buildRowDetalheHtml(BRL(r.valor), 'var(--verde)', notaFormatada, locked ? '' : `delR(${r.id})`, locked ? '' : `editarDet(${r.id}, 'receita', ${r.valor}, '${descricaoEscaped}', false, '${notaEscaped}')`);
    }).join('');
  } else {
    const r = await fetch(`/api/despesas_detalhe/${ano}/${mes}/${encodeURIComponent(cat)}?_=${Date.now()}`);
    const rows = await r.json();
    const visiveis = rows.filter(r => !idsRemovidos.includes(r.id));
    
    let htmlFixas = '';
    let totalFixas = 0;
    const catObj = (dados.categorias || []).find(c => c.nome === cat);
    if (catObj) {
      const excKey = catObj.id + '_' + mes;
      const fixaExcluida = (dados.fixas_excecoes || {})[excKey] || false;
      const fixasApp = (dados.fixas || []).filter(f => f.cat_id === catObj.id || (catObj.inclui_fixas && !f.cat_id));
      const fixasAplicadasManual = dados.fixas_aplicadas_manual || {};
      
      let somaFixasAtivas = 0;
      let somaFixasExpiradas = 0;
      fixasApp.forEach(f => {
          const isExpiredAuto = window.isFixaExpirada && window.isFixaExpirada(f, mes, ano);
          const isAplicadaManual = fixasAplicadasManual[`${f.id}_${mes}`];
          if (isExpiredAuto || isAplicadaManual) somaFixasExpiradas += f.valor;
          else somaFixasAtivas += f.valor;
      });
      const somaFixasOriginal = somaFixasAtivas + somaFixasExpiradas;
      
      if (somaFixasOriginal > 0) {
        if (!fixaExcluida) {
          totalFixas = somaFixasAtivas;
          let label = '&#9906; ' + BRL(somaFixasAtivas);
          if (somaFixasExpiradas > 0) label += ` <span style="text-decoration:line-through;color:var(--text-muted);font-size:11px;margin-left:4px" title="Já aplicadas neste mês">${BRL(somaFixasExpiradas)}</span>`;
          htmlFixas = buildRowDetalheHtml(label, 'var(--azul)', 'Despesas Fixas (Restantes)', locked ? '' : `toggleFixaExcecaoModal(${catObj.id}, ${mes}, true)`, '');
        } else {
          htmlFixas = `<div class="di" style="opacity:0.6; background:var(--cinza)">
            <div class="di-texts">
              <span class="di-val" style="color:var(--text-muted); text-decoration:line-through">&#9906; ${BRL(somaFixasOriginal)}</span>
              <span class="di-desc" style="color:var(--text-muted)">Despesas Fixas (Removidas)</span>
            </div>
            ${locked ? '' : `<button class="btn-restore" onclick="toggleFixaExcecaoModal(${catObj.id}, ${mes}, false)" title="Restaurar fixas neste mês">&#8617;</button>`}
          </div>`;
        }
      }
    }

    const total = visiveis.reduce((s, r) => s + (r.valor || 0), 0) + totalFixas;
    const tituloFormatado = window.formatBankIcons ? window.formatBankIcons(detCtx.tit || '') : (detCtx.tit || '');
    document.getElementById('detT').innerHTML = `${tituloFormatado} <span style="font-size:13px; font-weight:bold; color:var(--text-main); background:var(--borda); padding:3px 8px; border-radius:12px; margin-left:6px; vertical-align:middle">${BRL(total)}</span>`;

    if (!visiveis.length && !htmlFixas) { el.innerHTML = '<p class="empty-state">Nenhum lançamento.</p>'; return; }
    const htmlDesp = visiveis.map(r => {
      const ehCartao = r.ignorar_total === 1 || r.ignorar_total === true;
      const icone = ehCartao ? '&#9645; ' : '';
      const cor = ehCartao ? 'var(--text-muted)' : (r.valor < 0 ? 'var(--vermelho)' : 'var(--verde)');
      let notaFormatada = ehCartao ? (r.nota ? r.nota + ' (Não somado)' : 'Cartão (Não somado)') : r.nota;
      if (window.formatBankIcons) notaFormatada = window.formatBankIcons(notaFormatada);
      const notaEscaped = window.escapeJsSingleQuoted ? window.escapeJsSingleQuoted(r.nota || '') : (r.nota || '').replace(/'/g, "\\'");
      return buildRowDetalheHtml(icone + BRL(r.valor), cor, notaFormatada, locked ? '' : `delD(${r.id})`, locked ? '' : `editarDet(${r.id}, 'despesa', ${r.valor}, '${notaEscaped}', ${ehCartao})`);
    }).join('');
    
    el.innerHTML = htmlDesp + htmlFixas; // Adiciona as fixas no final da lista
  }
}

window.toggleFixaExcecaoModal = async function(catId, mes, excluir) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) {
    alert('Este ano está travado. Desbloqueie primeiro para alterar.');
    return;
  }
  try {
    const res = await fetch('/api/fixa_excecao', {
      method: excluir ? 'POST' : 'DELETE',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ano: ano, mes: mes, cat_id: catId})
    });
    if (!res.ok) throw new Error('Falha ao alterar fixas');
    
    detUndoManager.push({ type: 'toggle_fixas', catId, mes, excluir: !excluir });
    
    await debouncedLoad();
    await carregarDetLocal();
  } catch (error) { alert(error.message); }
};

async function desfazerDet() {
  await detUndoManager.undo(debouncedLoad, carregarDetLocal);
}

async function fecharEefetivarDet() {
  if (await flushDeleteQueue(detDeleteQueue, item => item.tipo === 'receita' ? '/api/receita/' + item.id : '/api/despesa/' + item.id)) {
    detDeleteQueue = [];
    detUndoManager.clear();
    await debouncedLoad();
  }
  editandoId = null;
  editandoTipo = null;
  toggleEditUiDet(false, false);
  fecharModal('ovDet');
}

async function addLanc() {
  const sucesso = await executarLancamentoDet();
  if (!sucesso) return;
  document.getElementById('aV').value = '';
  document.getElementById('aN').value = '';
  if (document.getElementById('detMesEditar')) document.getElementById('detMesEditar').value = String(detCtx.mes || 1);
  if (document.getElementById('detIgnorar')) document.getElementById('detIgnorar').checked = false;
  await carregarDetLocal();
  await debouncedLoad();
}
