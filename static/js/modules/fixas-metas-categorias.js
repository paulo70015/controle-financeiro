﻿var renCtx = {};

function renderFixas() {
  const ulLf = document.getElementById('lf');
  if (!ulLf) return;
  const fx = dados.fixas || [];
  
  // Calcular mês fiscal atual
  const hoje = new Date();
  const diaAtual = hoje.getDate();
  let mesAtualNum = hoje.getMonth() + 1;
  let anoAtualNum = hoje.getFullYear();
  
  const diaInicio = (typeof _cfgDiaInicioMesFiscal !== 'undefined') ? _cfgDiaInicioMesFiscal : 25;
  
  // Lógica de competência do cartão:
  // Antes do fechamento: mês atual + 1 (despesas vão para próxima fatura)
  // Depois do fechamento: mês atual + 2 (cartão já fechou, despesas vão para fatura seguinte)
  if (diaAtual >= diaInicio) {
    mesAtualNum += 2; // Cartão fechou, próximo mês fiscal é +2
  } else {
    mesAtualNum += 1; // Antes do fechamento, próximo mês fiscal é +1
  }
  
  // Ajustar ano se necessário
  if (mesAtualNum > 12) {
    mesAtualNum = mesAtualNum - 12;
    anoAtualNum += 1;
  }
  
  const mesAtualStr = typeof MESES !== 'undefined' ? MESES[mesAtualNum - 1] : '';
  const fixasAplicadasManual = dados.fixas_aplicadas_manual || {};
  
  // Atualizar info do mês fiscal
  const elMesFiscalInfo = document.getElementById('mesFiscalInfo');
  if (elMesFiscalInfo) {
    elMesFiscalInfo.textContent = `Competência: ${mesAtualStr}/${anoAtualNum}`;
  }
  
  let somaTotal = 0;
  let somaRestante = 0;

  ulLf.innerHTML = fx.map(f => {
    const isExpiredAuto = window.isFixaExpirada && window.isFixaExpirada(f, mesAtualNum, anoAtualNum);
    const isAplicadaManual = fixasAplicadasManual[`${f.id}_${mesAtualNum}`];
    const isExpired = isExpiredAuto || isAplicadaManual;
    
    const expStyle = isExpired ? 'text-decoration:line-through;color:var(--text-muted)' : 'color:var(--text-main)';
    const expLabel = isExpired ? ` <span style="font-size:10px;font-weight:normal;color:var(--text-muted);text-decoration:none">(${mesAtualStr} aplicado${isAplicadaManual ? ' ✓' : ''})</span>` : '';
    const descFormatada = window.formatBankIcons ? window.formatBankIcons(f.descricao) : f.descricao;
    
    somaTotal += f.valor;
    if (!isExpired) somaRestante += f.valor;
    
    // Botão de aplicar/desaplicar manual
    const btnAplicar = isAplicadaManual 
      ? `<button class="btn-aplicar-fixa aplicada" onclick="toggleFixaAplicadaManual(${f.id}, ${mesAtualNum}, false)" title="Desmarcar como aplicada">✓</button>`
      : (isExpiredAuto 
          ? '' 
          : `<button class="btn-aplicar-fixa" onclick="toggleFixaAplicadaManual(${f.id}, ${mesAtualNum}, true)" title="Marcar como aplicada">✓</button>`);

    return `<div class="di" id="fxli-${f.id}" style="padding:4px 0">
      <div style="flex:1;display:flex;flex-direction:column;gap:0">
        <span style="font-weight:600;font-size:12px;${expStyle}">${BRL(f.valor)}${expLabel}</span>
        <span style="color:var(--text-muted);font-size:11px">${descFormatada} (Dia ${f.dia||'?'})</span>
      </div>
      ${btnAplicar}
      <button class="btn-edit" onclick="editarFxInline(${f.id})" title="Editar">&#9998;</button>
      <button class="btn-delete" onclick="delFx(${f.id})" title="Excluir">&#10005;</button>
    </div>`;
  }).join('');
  
  const elTf = document.getElementById('tf');
  if (elTf) {
    elTf.innerHTML = `Total: ${BRL(somaTotal)} <br><span style="font-size:12px;color:var(--text-muted);font-weight:normal">Restante no mês: <b style="color:var(--text-main)">${BRL(somaRestante)}</b></span>`;
  }
}

function renderMetas() {
  const divLm = document.getElementById('lm');
  if (!divLm) return;
  divLm.innerHTML = (dados.metas || []).map(m => {
    const descFormatada = window.formatBankIcons ? window.formatBankIcons(m.descricao) : m.descricao;
    return `
    <div class="mi ${m.concluida?'done':''}" id="mli-${m.id}">
      <input type="checkbox" ${m.concluida?'checked':''} onchange="togMeta(${m.id},this.checked)">
      <span class="mn">${descFormatada}</span>
      <span class="mv">${m.valor?BRL(m.valor):''}</span>
      <span class="ma" style="margin-right:4px">${m.ano_meta||'N/A'}</span>
      <button class="btn-edit" onclick="editarMInline(${m.id})" title="Editar">&#9998;</button>
      <button class="btn-delete" onclick="delMeta(${m.id})" title="Excluir">&#10005;</button>
    </div>`
  }).join('');
}

function abrirRen(id, nome, fixaFlag = 0, contaVinculadaId = null, tooltip = '') {
  renCtx = {id, nomeOriginal: nome};
  document.getElementById('renN').value = nome;
  document.getElementById('renTooltip').value = tooltip;
  const cat = (dados.categorias || []).find(c => c.id === id);
  document.getElementById('renCartao').checked = cat ? !!cat.is_cartao : false;
  const outraTemFixas = (dados.categorias || []).some(c => c.inclui_fixas && c.id !== id);
  const rowRenFixas = document.getElementById('renFixas').closest('.fr');
  if (outraTemFixas) {
    rowRenFixas.style.display = 'none';
    document.getElementById('renFixas').checked = false;
  } else {
    rowRenFixas.style.display = '';
    document.getElementById('renFixas').checked = !!fixaFlag;
  }
  const sel = document.getElementById('renConta');
  const info = document.getElementById('renContaInfo');
  window.popularSelectContas(sel, contaVinculadaId, info);
  abrirModal('ovRen');
  setTimeout(() => { if (window.injectBankSelector) window.injectBankSelector('renN'); }, 100);
  setTimeout(() => document.getElementById('renN').select(), 100);
}

async function confirmarRen() {
  const nome = document.getElementById('renN').value.trim();
  if (!nome) return alert('Nome não pode ser vazio');
  const inclui_fixas = document.getElementById('renFixas').checked ? 1 : 0;
  const contaVal = document.getElementById('renConta').value;
  const conta_vinculada_id = contaVal ? parseInt(contaVal) : null;
  const tooltip = document.getElementById('renTooltip').value.trim();
  const is_cartao = document.getElementById('renCartao').checked ? 1 : 0;
  try {
    await safeApiCall('/api/categoria/' + renCtx.id, {
      method: 'PUT',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({tooltip, nome, inclui_fixas, conta_vinculada_id, is_cartao, nome_original: renCtx.nomeOriginal})
    });
    fecharModal('ovRen');
    debouncedLoad();
  } catch (error) {
    alert('Erro ao editar categoria: ' + error.message);
  }
}

function buildFormEditFixaHtml(f) {
  const isEdit = !!f;
  const fId = isEdit ? f.id : 'null';
  const d = isEdit ? f.descricao : '';
  const di = isEdit ? (f.dia || '') : '';
  const v = isEdit ? parseFloat(f.valor).toLocaleString('pt-BR', {minimumFractionDigits:2}) : '';
  return `
    <div class="inline-edit-box">
      <div class="inline-edit-row">
        <input id="fxeV" type="text" inputmode="decimal" class="inline-edit-input" value="${v}" placeholder="Valor (R$)">
        <input id="fxeDi" type="number" inputmode="numeric" class="inline-edit-input short" value="${di}" placeholder="Dia" min="1" max="31">
      </div>
      <input id="fxeD" type="text" class="inline-edit-input" value="${d}" placeholder="Descrição">
      <div class="inline-edit-actions">
        <button class="btn bs inline-edit-btn" onclick="cancelarFxInline()">Cancelar</button>
        <button class="btn bv bs inline-edit-btn" onclick="salvarFxInline(${fId})">${isEdit ? 'Alterar' : '+ Lançar'}</button>
      </div>
    </div>`;
}

function resetEditInline(tipo) {
  document.querySelectorAll(`.${tipo}-edit-row`).forEach(el => el.remove());
  const itemClass = tipo === 'fx' ? '.di' : '.mi';
  document.querySelectorAll(`${itemClass}.${tipo}-editing`).forEach(el => el.classList.remove(`${tipo}-editing`));
}

function abrirF() {
  resetEditInline('fx');

  const ul = document.getElementById('lf');
  const div = document.createElement('div');
  div.className = 'fx-edit-row';
  div.innerHTML = buildFormEditFixaHtml(null);
  ul.insertBefore(div, ul.firstChild);
  setTimeout(() => document.getElementById('fxeD').focus(), 50);
}

function editarFxInline(id) {
  resetEditInline('fx');

  const f = dados.fixas.find(x => x.id === id);
  if (!f) return;
  const li = document.getElementById('fxli-' + id);
  if (!li) return;
  li.classList.add('fx-editing');

  const div = document.createElement('div');
  div.className = 'fx-edit-row';
  div.innerHTML = buildFormEditFixaHtml(f);
  li.insertAdjacentElement('afterend', div);
  setTimeout(() => document.getElementById('fxeD').select(), 50);
}

function cancelarFxInline() {
  resetEditInline('fx');
}

async function salvarFxInline(id) {
  const d = document.getElementById('fxeD').value.trim();
  const di = document.getElementById('fxeDi').value;
  const v = parseVal(document.getElementById('fxeV').value);
  if (!d || v === null) return alert('Preencha todos os campos');

  try {
    if (id) {
      await safeApiCall('/api/fixa/' + id, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({descricao:d, dia:di, valor:v, cat_id: null})
      });
    } else {
      await safeApiCall('/api/fixa', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({descricao:d, dia:di, valor:v, cat_id: null, ano})
      });
    }
    cancelarFxInline();
    await debouncedLoad();
  } catch (error) {
    alert('Erro ao salvar despesa fixa: ' + error.message);
  }
}

async function delFx(id) {
  if (!confirm('Remover despesa fixa?')) return;
  try {
    await safeApiCall('/api/fixa/' + id, {method:'DELETE'});
    debouncedLoad();
  } catch (error) { alert(error.message); }
}

async function toggleFixaExcecao(catId, mes, excluir) {
  try {
    await safeApiCall('/api/fixa_excecao', {
      method: excluir ? 'POST' : 'DELETE',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ano: ano, mes: mes, cat_id: catId})
    });
    await debouncedLoad();
  } catch (error) { alert(error.message); }
}

function buildFormEditMetaHtml(m, anoAtual) {
  const isEdit = !!m;
  const mId = isEdit ? m.id : 'null';
  const d = isEdit ? m.descricao : '';
  const a = isEdit ? (m.ano_meta || '') : anoAtual;
  const v = isEdit ? (m.valor || '') : '';
  return `
    <div class="inline-edit-box" style="background:var(--bg-linha-total-contas);">
      <input id="m-exeD" type="text" class="inline-edit-input" value="${d}" placeholder="Descrição">
      <div class="inline-edit-row">
        <input id="m-exeA" type="number" inputmode="numeric" class="inline-edit-input short" style="width:70px" value="${a}" placeholder="Ano alvo" title="Ano sugerido para concluir">
        <input id="m-exeV" type="text" inputmode="decimal" class="inline-edit-input" value="${v}" placeholder="Valor alvo">
      </div>
      <div class="inline-edit-actions">
        <button class="btn bs inline-edit-btn" onclick="cancelarMInline()">Cancelar</button>
        <button class="btn bv bs inline-edit-btn" onclick="salvarMInline(${mId})">Salvar</button>
      </div>
    </div>`;
}

function abrirM() {
  resetEditInline('m');

  const div = document.createElement('div');
  div.className = 'm-edit-row';
  div.innerHTML = buildFormEditMetaHtml(null, ano);
  const lm = document.getElementById('lm');
  lm.insertBefore(div, lm.firstChild);
  setTimeout(() => document.getElementById('m-exeD').focus(), 50);
}

function editarMInline(id) {
  resetEditInline('m');

  const m = dados.metas.find(x => x.id === id);
  if (!m) return;
  const divMi = document.getElementById('mli-' + id);
  if (!divMi) return;
  divMi.classList.add('m-editing');

  const div = document.createElement('div');
  div.className = 'm-edit-row';
  div.innerHTML = buildFormEditMetaHtml(m, ano);
  divMi.insertAdjacentElement('afterend', div);
  setTimeout(() => document.getElementById('m-exeD').select(), 50);
}

function cancelarMInline() {
  resetEditInline('m');
}

async function salvarMInline(id) {
  const d = document.getElementById('m-exeD').value.trim();
  const v = parseVal(document.getElementById('m-exeV').value) || 0;
  const a = document.getElementById('m-exeA').value;
  if (!d) return alert('Informe a descrição');

  try {
    if (id) {
      await safeApiCall('/api/meta/' + id, {
        method:'PUT',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({descricao:d, valor:v, ano_meta:a||null})
      });
    } else {
      await safeApiCall('/api/meta', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({descricao:d, valor:v, ano_meta:a||null, ano_criacao:ano})
      });
    }
    cancelarMInline();
    await debouncedLoad();
  } catch (error) {
    alert('Erro ao salvar meta: ' + error.message);
  }
}

async function togMeta(id, c) {
  try {
    await safeApiCall('/api/meta/' + id, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({concluida:c?1:0})
    });
    debouncedLoad();
  } catch (error) { alert(error.message); }
}

async function delMeta(id) {
  if (!confirm('Remover meta?')) return;
  try {
    await safeApiCall('/api/meta/' + id, {method:'DELETE'});
    debouncedLoad();
  } catch (error) { alert(error.message); }
}

async function salvarC() {
  const n = document.getElementById('cN').value.trim();
  if (!n) return alert('Informe o nome');
  const inclui_fixas = document.getElementById('cFixas').checked ? 1 : 0;
  const is_cartao = document.getElementById('cCartao').checked ? 1 : 0;
  const contaVal = document.getElementById('cConta').value;
  const conta_vinculada_id = contaVal ? parseInt(contaVal) : null;
  const tooltip = document.getElementById('cTooltip').value.trim();
  try {
    await safeApiCall('/api/categoria', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nome:n, inclui_fixas, is_cartao, conta_vinculada_id, tooltip, ano})
    });
    fecharModal('ovC');
    document.getElementById('cN').value = '';
    document.getElementById('cFixas').checked = false;
    document.getElementById('cCartao').checked = false;
    document.getElementById('cConta').value = '';
    document.getElementById('cTooltip').value = '';
    debouncedLoad();
  } catch (error) {
    alert('Erro ao criar categoria: ' + error.message);
  }
}

function abrirC() {
  document.getElementById('cN').value = '';
  document.getElementById('cFixas').checked = false;
  document.getElementById('cCartao').checked = false;
  document.getElementById('cTooltip').value = '';
  const sel = document.getElementById('cConta');
  sel.innerHTML = '<option value="">— Sem vínculo de conta —</option>';
  (dados.contas || []).forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = '❖ ' + c.nome;
    sel.appendChild(opt);
  });
  const info = document.getElementById('cContaInfo');
  info.style.display = 'none';
  sel.onchange = () => {
    info.style.display = sel.value ? 'block' : 'none';
  };
  const jaTemFixas = (dados.categorias || []).some(c => c.inclui_fixas);
  const rowFixas = document.getElementById('cFixas').closest('.fr');
  if (jaTemFixas) {
    rowFixas.style.display = 'none';
    document.getElementById('cFixas').checked = false;
  } else {
    rowFixas.style.display = '';
  }
  abrirModal('ovC');
  setTimeout(() => { if (window.injectBankSelector) window.injectBankSelector('cN'); }, 100);
  setTimeout(() => document.getElementById('cN').focus(), 100);
}

function novaCatInline() {
  const box = document.getElementById('novaCatBox');
  box.style.display = 'block';
  setTimeout(() => { if (window.injectBankSelector) window.injectBankSelector('novaCatNome'); }, 100);
  setTimeout(() => document.getElementById('novaCatNome').focus(), 100);
}

function cancelarCatInline() {
  document.getElementById('novaCatBox').style.display = 'none';
  document.getElementById('novaCatNome').value = '';
}

async function confirmarCatInline() {
  const nome = document.getElementById('novaCatNome').value.trim();
  if (!nome) return alert('Informe o nome da categoria');
  try {
    await safeApiCall('/api/categoria', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nome, inclui_fixas:0, ano})
    });
    const rd = await safeApiCall('/api/dados/' + ano);
    dados = await rd.json();
    popularSel();
    const sel = document.getElementById('dC');
    for (let i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === nome) {
        sel.selectedIndex = i;
        break;
      }
    }
    cancelarCatInline();
  } catch (error) {
    alert('Erro ao criar categoria: ' + error.message);
  }
}

let dragSrcId = null;

function dragStart(e, catId) {
  dragSrcId = catId;
  e.dataTransfer.effectAllowed = 'move';
}

function dragOver(e) {
  e.preventDefault();
  e.currentTarget.classList.add('drag-over');
  e.dataTransfer.dropEffect = 'move';
}

function dragLeave(e) {
  e.currentTarget.classList.remove('drag-over');
}

async function dragDrop(e, targetId) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  if (dragSrcId === null || dragSrcId === targetId) return;
  const rows = [...document.querySelectorAll('tr.cat-row')];
  const ids = rows.map(r => parseInt(r.dataset.catId));
  const fromIdx = ids.indexOf(dragSrcId);
  const toIdx = ids.indexOf(targetId);
  if (fromIdx === -1 || toIdx === -1) return;
  ids.splice(fromIdx, 1);
  ids.splice(toIdx, 0, dragSrcId);
  await fetch('/api/categorias/reordenar', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ordem:ids})
  });
  debouncedLoad();
}


async function toggleFixaAplicadaManual(fixaId, mes, aplicar) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return;
  
  try {
    await safeApiCall('/api/fixa_aplicada_manual', {
      method: aplicar ? 'POST' : 'DELETE',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ano: ano, mes: mes, fixa_id: fixaId})
    });
    await debouncedLoad();
  } catch (error) { 
    alert(error.message); 
  }
}
