﻿﻿﻿﻿﻿var depCtx = {};
var editContaCtx = {};
var movCtx = {};
var movDeleteQueue = [];
var movUndoStack = [];
var movEditando = false;
var movOriginalData = null;

function getMovimentacoesMes(mes) {
  const mv = dados.movimentacoes ? dados.movimentacoes[mes] : null;
  if (!mv) return [];
  if (Array.isArray(mv)) return mv;
  if (Array.isArray(mv.items)) return mv.items;
  return mv.valor !== undefined ? [mv] : [];
}

function totalMovimentacoesMes(mes) {
  const mv = dados.movimentacoes ? dados.movimentacoes[mes] : null;
  if (!mv) return 0;
  if (typeof mv.valor === 'number') return mv.valor;
  return getMovimentacoesMes(mes).reduce((s, r) => s + (r.valor || 0), 0);
}

function injetarLayoutModalDRY(modalId, cfg) {
  const ov = document.getElementById(modalId);
  if (!ov) return;
  const mo = ov.querySelector('.mo');
  if (mo && !mo.dataset.dry) {
    mo.dataset.dry = 'true';
    mo.innerHTML = `
      <div class="modal-top-bar">
        ${cfg.title}
      </div>
      <div class="dl" id="${cfg.listId}"></div>
      <div class="action-bar-wrap">
        ${cfg.inputs}
        <button class="btn bv bs" ${cfg.btnSaveId ? `id="${cfg.btnSaveId}"` : ''} onclick="${cfg.fnSave}">+ Lançar</button>
      </div>
      <div class="mb">
        <button class="btn btn-undo" id="${cfg.btnUndoId}" style="display:none;" onclick="${cfg.fnUndo}">↩ Desfazer</button>
        <button class="btn" onclick="${cfg.fnClose}">Fechar</button>
        <button class="btn ba" ${cfg.btnSaveCloseId ? `id="${cfg.btnSaveCloseId}"` : ''} onclick="${cfg.fnSaveClose}">Salvar e fechar</button>
      </div>
    `;
  }
}

function abrirConta() {
  document.getElementById('ctN').value = '';
  document.getElementById('ctSI').value = '';
  abrirModal('ovConta');
  setTimeout(() => document.getElementById('ctN').focus(), 200);
}

async function salvarConta() {
  const n = document.getElementById('ctN').value.trim();
  if (!n) return alert('Informe o nome da conta');
  const si = parseVal(document.getElementById('ctSI').value) || 0;
  try {
    await safeApiCall('/api/conta', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nome:n, saldo_inicial:si})
    }, 'Falha ao salvar conta.');
    fecharModal('ovConta');
    debouncedLoad();
  } catch (error) {
    console.error('Erro em salvarConta:', error);
    alert('Erro: ' + error.message);
  }
}

async function confirmarDelConta(id) {
  if (!confirm('Excluir esta conta e todas as movimentações?')) return;
  try {
    await safeApiCall('/api/conta/' + id, {method:'DELETE'}, 'Falha ao excluir conta.');
    debouncedLoad();
  } catch (error) {
    console.error('Erro em confirmarDelConta:', error);
    alert('Erro: ' + error.message);
  }
}

function abrirEditConta(id, nome, saldoIni) {
  editContaCtx = {id};
  document.getElementById('ecN').value = nome;
  document.getElementById('ecSI').value = saldoIni ? parseFloat(saldoIni).toLocaleString('pt-BR', {minimumFractionDigits: 2}) : '';
  abrirModal('ovEditConta');
  setTimeout(() => document.getElementById('ecN').focus(), 200);
}

async function salvarEditConta() {
  const n = document.getElementById('ecN').value.trim();
  const si = parseVal(document.getElementById('ecSI').value) || 0;
  try {
    await safeApiCall('/api/conta/' + editContaCtx.id, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nome:n, saldo_inicial:si})
    }, 'Falha ao salvar alterações na conta.');
    fecharModal('ovEditConta');
    debouncedLoad();
  } catch (error) {
    console.error('Erro em salvarEditConta:', error);
    alert('Erro: ' + error.message);
  }
}

function abrirDep(contaId, contaNome, mes) {
  const tit = contaNome + ' - ' + MESES[mes - 1];
  depCtx = {contaId, mes, contaNome, tit};
  depDeleteQueue = [];
  depUndoManager.clear();

  injetarLayoutModalDRY('ovDep', {
    title: '<h3 id="depContaNome"></h3>',
    listId: 'depL',
    inputs: `
      <input type="text" inputmode="decimal" id="depV" placeholder="Valor (R$)" class="ab-val">
      <input type="text" id="depN" placeholder="Nota" class="ab-nota">
    `,
    fnSave: 'salvarDeposito()',
    btnUndoId: 'depBtnUndo',
    fnUndo: 'desfazerDep()',
    fnClose: 'fecharEefetivarDep()',
    fnSaveClose: 'salvarDepositoEFechar()'
  });

  const depBtnUndo = document.getElementById('depBtnUndo');
  if (depBtnUndo) depBtnUndo.style.display = 'none';
  const tituloFormatado = window.formatBankIconsSafe ? window.formatBankIconsSafe(tit) : tit;
  const depContaNome = document.getElementById('depContaNome');
  const depV = document.getElementById('depV');
  const depN = document.getElementById('depN');
  if (!depContaNome || !depV || !depN) {
    alert('Não foi possível abrir o modal de movimentações.');
    return;
  }
  depContaNome.innerHTML = tituloFormatado;
  depV.value = '';
  depN.value = '';
  const saldoAtual = (dados.saldos && dados.saldos[String(contaId)]) ?
    (dados.saldos[String(contaId)][mes] || 0) : 0;
  const elS = document.getElementById('depSaldoAtual');
  if (elS) {
    elS.textContent = BRL(saldoAtual);
    elS.style.color = saldoAtual < 0 ? 'var(--vermelho)' : 'var(--verde)';
    const labelAno = document.getElementById('depLabelAno');
    if (labelAno) labelAno.remove();
  }
  const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
  depV.disabled = locked;
  depN.disabled = locked;
  const b1 = document.querySelector('button[onclick="salvarDeposito()"]');
  const b2 = document.querySelector('button[onclick="salvarDepositoEFechar()"]');
  if (b1) b1.style.display = locked ? 'none' : 'inline-block';
  if (b2) b2.style.display = locked ? 'none' : 'inline-block';
  
  carregarDep(contaId, mes);
  abrirModal('ovDep');
  setTimeout(() => { if (depV) depV.focus(); }, 200);
}

async function carregarDep(contaId, mes) {
  const el = document.getElementById('depL');
  if (!el) return;
  try {
    const response = await safeApiCall(`/api/depositos_detalhe/${ano}/${mes}/${contaId}?_=${Date.now()}`, {}, 'Falha ao carregar movimentações.');
    const rows = await response.json();
    const visiveis = rows.filter(r => !depDeleteQueue.includes(r.id));

    const movsConta = getMovimentacoesMes(mes).filter(mov => String(mov.conta_id) === String(contaId));
    const movValor = movsConta.reduce((s, mov) => s + (mov.valor || 0), 0);

    let despesasVincMes = 0;
    (dados.categorias || []).filter(c => String(c.conta_vinculada_id) === String(contaId)).forEach(cat => {
      const d = (dados.despesas && dados.despesas[cat.nome]) ? dados.despesas[cat.nome][mes] : null;
      const vLanc = d ? (d.valor || 0) : 0;
      const fixasDaCat = (dados.fixas || []).filter(f => f.cat_id === cat.id || (cat.inclui_fixas && !f.cat_id));
      const fixasAplicadasManual = dados.fixas_aplicadas_manual || {};
      let vFixasAtivas = 0;
      fixasDaCat.forEach(f => {
        const isExpiredAuto = window.isFixaExpirada && window.isFixaExpirada(f, mes, ano);
        const isAplicadaManual = fixasAplicadasManual[`${f.id}_${mes}`];
        if (isExpiredAuto || isAplicadaManual) return;
        vFixasAtivas += f.valor;
      });
      const excKey = cat.id + '_' + mes;
      const fixaExcluida = (dados.fixas_excecoes || {})[excKey] || false;
      despesasVincMes += (vLanc + (!fixaExcluida ? vFixasAtivas : 0));
    });

    const totalDeps = visiveis.reduce((s, r) => s + (r.valor || 0), 0);
    const total = totalDeps + movValor - despesasVincMes;

    const corTxt = total < 0 ? 'var(--vermelho)' : 'var(--verde)';
    const corFundo = total < 0 ? 'var(--cor-fundo-travado)' : 'var(--bg-st2)';
    const tituloFormatado = window.formatBankIconsSafe ? window.formatBankIconsSafe(depCtx.tit || '') : (depCtx.tit || '');
    const depContaNome = document.getElementById('depContaNome');
    if (depContaNome) {
      depContaNome.innerHTML = `${tituloFormatado} <span class="modal-badge" style="color:${corTxt}; background:${corFundo};" title="Variação líquida no mês">${BRL(total)}</span>`;
    }

    const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
    let htmlMovs = visiveis.map(r => {
      const notaEscaped = window.escapeJsSingleQuoted ? window.escapeJsSingleQuoted(r.nota || '') : (r.nota || '').replace(/'/g, "\\'");
      const valTxt = r.valor < 0 ? `-${BRL(r.valor)}` : BRL(r.valor);
      return buildRowDetalheHtml(valTxt, r.valor < 0 ? 'var(--vermelho)' : 'var(--verde)', r.nota, locked ? '' : `delDep(${r.id})`, locked ? '' : `editarDep(${r.id}, ${r.valor}, '${notaEscaped}')`);
    }).join('');

    if (despesasVincMes > 0) {
      htmlMovs = buildRowDetalheHtml(BRL(-despesasVincMes), 'var(--vermelho)', 'Despesas Vinculadas (Mês)') + htmlMovs;
    }

    movsConta.slice().reverse().forEach(mov => {
      const movNota = mov.nota ? `Movimentação Geral: ${mov.nota}` : 'Movimentação Geral';
      const movVal = mov.valor || 0;
      const movColor = movVal < 0 ? 'var(--vermelho)' : 'var(--verde)';
      const movNotaEscaped = window.escapeJsSingleQuoted ? window.escapeJsSingleQuoted(mov.nota || '') : (mov.nota || '').replace(/'/g, "\\'");
      const movValTxt = movVal < 0 ? `-${BRL(movVal)}` : BRL(movVal);
      htmlMovs = buildRowDetalheHtml(
        movValTxt,
        movColor,
        movNota,
        locked ? '' : `delMovFromDep(${mov.id})`,
        locked ? '' : `editarMovFromDep(${mov.id}, ${mov.conta_id}, ${movVal}, '${movNotaEscaped}')`,
      ) + htmlMovs;
    });

    if (mes === 1) {
      const conta = (dados.contas || []).find(c => String(c.id) === String(contaId));
      const saldoInicial = conta ? (conta.saldo_inicial || 0) : 0;
      const saldoAtualJan = (dados.saldos && dados.saldos[String(contaId)]) ? (dados.saldos[String(contaId)][1] || 0) : 0;
      
      const saldoBaseCalculado = saldoAtualJan - total;
      const saldoBase = (dados.saldos && dados.saldos[String(contaId)] && dados.saldos[String(contaId)]['0'] !== undefined) 
                            ? dados.saldos[String(contaId)]['0'] 
                            : saldoBaseCalculado;
      const saldoHerdado = saldoBase - saldoInicial;
      
      let linhasIniciais = '';
      
      if (saldoHerdado !== 0) {
        linhasIniciais += buildRowDetalheHtml(BRL(saldoHerdado), 'var(--text-main)', `Saldo herdado (Dez. ${ano - 1})`);
      }
      if (saldoInicial !== 0) {
        linhasIniciais += buildRowDetalheHtml(BRL(saldoInicial), 'var(--text-main)', 'Saldo inicial da conta');
      }
      
      if (!linhasIniciais && visiveis.length === 0 && movValor === 0 && despesasVincMes === 0) {
        linhasIniciais = buildRowDetalheHtml(BRL(0), 'var(--text-main)', 'Saldo base zerado');
      }
      htmlMovs = linhasIniciais + htmlMovs;
    }

    if (!htmlMovs) {
      el.innerHTML = '<p style="color:var(--text-muted);font-size:12px;padding:4px 0">Nenhuma movimentação neste mês.</p>';
      return;
    }
    el.innerHTML = htmlMovs;
  } catch (error) {
    console.error('Erro em carregarDep:', error);
    el.innerHTML = `<p style="color:var(--vermelho);font-size:12px;padding:4px 0">Erro ao carregar: ${error.message}</p>`;
  }
}

async function salvarDeposito() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  const depV = document.getElementById('depV');
  const depN = document.getElementById('depN');
  if (!depV || !depN) return alert('Não foi possível salvar a movimentação.');
  const v = parseVal(depV.value);
  if (v === null || v === 0) return alert('Informe o valor (positivo para depósito, negativo para saque)');
  const n = depN.value;
  try {
        const isEdit = typeof depEditandoId !== 'undefined' && depEditandoId !== null;
        const url = isEdit ? '/api/deposito/' + depEditandoId : '/api/deposito';
        const method = isEdit ? 'PUT' : 'POST';
        const body = isEdit ? {valor: v, nota: n} : {ano, mes:depCtx.mes, conta_id:depCtx.contaId, valor:v, nota:n};

        await safeApiCall(url, {
          method: method,
      headers:{'Content-Type':'application/json'},
          body: JSON.stringify(body)
    }, 'Falha ao salvar depósito.');
        if (isEdit && typeof depUndoManager !== 'undefined') {
          depUndoManager.push({ type: 'edit', url, oldBody: { valor: depOriginalData.valor, nota: depOriginalData.nota || '' } });
        }
        if (typeof depEditandoId !== 'undefined') depEditandoId = null;
        if (typeof toggleEditUiDet !== 'undefined') toggleEditUiDet(false, true);
    depV.value = '';
    depN.value = '';
    await debouncedLoad();
    const saldoAtual = (dados.saldos && dados.saldos[String(depCtx.contaId)]) ?
      (dados.saldos[String(depCtx.contaId)][depCtx.mes] || 0) : 0;
    const elS = document.getElementById('depSaldoAtual');
    if (elS) {
      elS.textContent = BRL(saldoAtual);
      elS.style.color = saldoAtual < 0 ? 'var(--vermelho)' : 'var(--verde)';
      const labelAno = document.getElementById('depLabelAno');
      if (labelAno) labelAno.remove();
    }
    carregarDep(depCtx.contaId, depCtx.mes);
  } catch (error) {
    console.error('Erro em salvarDeposito:', error);
    alert('Erro: ' + error.message);
  }
}

async function delDep(id) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  depDeleteQueue.push(id);
  depUndoManager.push({type: 'delete', id: id});
  carregarDep(depCtx.contaId, depCtx.mes);
}

async function desfazerDep() {
  if (typeof depUndoManager !== 'undefined') {
    await depUndoManager.undo(debouncedLoad, () => carregarDep(depCtx.contaId, depCtx.mes));
  }
}

async function fecharEefetivarDep() {
  if (await flushDeleteQueue(depDeleteQueue, id => '/api/deposito/' + id)) {
    depDeleteQueue = [];
    depUndoManager.clear();
    await debouncedLoad();
  }
  if (typeof depEditandoId !== 'undefined') depEditandoId = null;
  if (typeof toggleEditUiDet !== 'undefined') toggleEditUiDet(false, true);
  fecharModal('ovDep');
}

async function salvarDepositoEFechar() {
  const depV = document.getElementById('depV');
  if (!depV) return fecharEefetivarDep();
  const v = parseVal(depV.value);
  if (v !== null && v !== 0) {
    await salvarDeposito();
  }
  await fecharEefetivarDep();
}

window.delMovFromDep = async function(id) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  if (!confirm('Excluir esta movimentação?')) return;
  try {
    await safeApiCall(`/api/movimentacao/${id}`, {method: 'DELETE'}, 'Falha ao excluir movimentação.');
    await debouncedLoad();
    carregarDep(depCtx.contaId, depCtx.mes);
  } catch (err) {
    alert('Erro: ' + err.message);
  }
};

window.editarMovFromDep = function(id, conta_id, valor, nota) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  fecharEefetivarDep();
  setTimeout(() => {
    abrirMov(depCtx.mes);
    setTimeout(() => editarMov(id, conta_id, valor, nota), 220);
  }, 50);
};

function abrirMov(mes) {
  movCtx = {mes};
  movDeleteQueue = [];
  movUndoStack = [];
  movEditando = false;
  movOriginalData = null;

  injetarLayoutModalDRY('ovMov', {
    title: '<h3>' + window.iconSVG('repeat', 'sm') + ' Movimentação - <span id="movMesNome"></span></h3>',
    listId: 'movL',
    inputs: `
      <select id="movConta" class="ab-select"></select>
      <input type="text" inputmode="decimal" id="movValor" placeholder="Valor (R$)" class="ab-val">
      <input type="text" id="movNota" placeholder="Nota" class="ab-nota">
    `,
    btnSaveId: 'movBtnSave',
    fnSave: 'salvarMov()',
    btnUndoId: 'movBtnUndo',
    fnUndo: 'desfazerMov()',
    fnClose: 'fecharEefetivarMov()',
    btnSaveCloseId: 'movBtnSaveClose',
    fnSaveClose: 'salvarMovEFechar()'
  });

  const lblMes = document.getElementById('movMesNome');
  if (lblMes) lblMes.textContent = MESES[mes - 1];
  
  const sel = document.getElementById('movConta');
  if (sel) {
    sel.innerHTML = '';
    (dados.contas || []).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = '❖ ' + c.nome;
      sel.appendChild(opt);
    });
    if (!sel.options.length) {
      alert('Cadastre uma conta corrente primeiro.');
      return;
    }
  }

  const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
  if (document.getElementById('movConta')) document.getElementById('movConta').disabled = locked;
  if (document.getElementById('movValor')) document.getElementById('movValor').disabled = locked;
  if (document.getElementById('movNota')) document.getElementById('movNota').disabled = locked;
  
  const btnSave = document.getElementById('movBtnSave');
  if (btnSave) btnSave.style.display = locked ? 'none' : 'inline-block';
  const btnSaveClose = document.getElementById('movBtnSaveClose');
  if (btnSaveClose) btnSaveClose.style.display = locked ? 'none' : 'inline-block';
  const btnUndo = document.getElementById('movBtnUndo');
  if (btnUndo) btnUndo.style.display = 'none';

  carregarMovLocal();
  abrirModal('ovMov');
  setTimeout(() => document.getElementById('movValor').focus(), 200);
}

window.editarMov = function(id, conta_id, valor, nota) {
  movEditando = true;
  movOriginalData = { id, conta_id, valor, nota };
  document.getElementById('movConta').value = conta_id;
  document.getElementById('movValor').value = (valor !== undefined && valor !== null && valor !== '') ? parseFloat(valor).toLocaleString('pt-BR', {minimumFractionDigits: 2}) : '';
  document.getElementById('movNota').value = nota || '';
  toggleEditUiMov(true);
  focarCampo('movValor');
};

function toggleEditUiMov(isEdit) {
  const b1 = document.getElementById('movBtnSave');
  const b2 = document.getElementById('movBtnSaveClose');
  if (b1) b1.textContent = isEdit ? 'Alterar' : '+ Lançar';
  if (b2) b2.textContent = isEdit ? 'Alterar e fechar' : 'Salvar e fechar';
}

function carregarMovLocal() {
  const el = document.getElementById('movL');
  const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
  
  if (!el) return;

  const rows = getMovimentacoesMes(movCtx.mes).filter(mv => !movDeleteQueue.includes(mv.id));
  if (!rows.length) {
    if (el) el.innerHTML = '<p class="empty-state">Nenhuma movimentação neste mês.</p>';
    return;
  }

  el.innerHTML = rows.map(mv => {
    const conta = (dados.contas || []).find(c => String(c.id) === String(mv.conta_id));
    const nomeConta = conta ? conta.nome : '';
    const texto = nomeConta ? `❖ ${nomeConta} ${mv.nota ? '- '+mv.nota : ''}` : (mv.nota || '');
    const notaEscaped = window.escapeJsSingleQuoted ? window.escapeJsSingleQuoted(mv.nota || '') : (mv.nota || '').replace(/'/g, "\\'");
    return buildRowDetalheHtml(
      BRL(mv.valor),
      mv.valor < 0 ? 'var(--vermelho)' : 'var(--verde)',
      texto,
      locked ? '' : `delMov(${mv.id})`,
      locked ? '' : `editarMov(${mv.id}, ${mv.conta_id}, ${mv.valor}, '${notaEscaped}')`
    );
  }).join('');
}

async function salvarMov() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado.');
  const v = parseVal(document.getElementById('movValor').value);
  if (v === null || v === 0) return alert('Informe o valor');
  const conta_id = parseInt(document.getElementById('movConta').value);
  const nota = document.getElementById('movNota').value;

  try {
    const isEdit = movEditando;
    const body = {ano, mes: movCtx.mes, conta_id, valor: v, nota};
    if (isEdit && movOriginalData?.id) body.id = movOriginalData.id;
    await safeApiCall('/api/movimentacao', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    }, 'Falha ao salvar movimentação.');

    if (isEdit) {
      movUndoStack.push({ type: 'edit', oldBody: {ano, mes: movCtx.mes, ...movOriginalData} });
      document.getElementById('movBtnUndo').style.display = 'inline-block';
    }

    movEditando = false;
    toggleEditUiMov(false);
    document.getElementById('movValor').value = '';
    document.getElementById('movNota').value = '';

    await debouncedLoad();
    carregarMovLocal();
  } catch (err) {
    alert('Erro: ' + err.message);
  }
}

function delMov(id) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  const mv = getMovimentacoesMes(movCtx.mes).find(item => item.id === id);
  if (!mv) return;

  movUndoStack.push({
    type: 'delete',
    oldData: {...mv}
  });
  const btnUndo = document.getElementById('movBtnUndo');
  if (btnUndo) btnUndo.style.display = 'inline-block';
  
  movDeleteQueue.push(id);
  carregarMovLocal();
}

async function desfazerMov() {
  if (!movUndoStack.length) return;
  const action = movUndoStack.pop();
  
  if (action.type === 'delete') {
    movDeleteQueue = movDeleteQueue.filter(id => id !== action.oldData.id);
  } else if (action.type === 'edit') {
    await safeApiCall('/api/movimentacao', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(action.oldBody)
    });
    await debouncedLoad();
  }
  
  carregarMovLocal();
  const btnUndo = document.getElementById('movBtnUndo');
  if (!movUndoStack.length && btnUndo) btnUndo.style.display = 'none';
}

async function fecharEefetivarMov() {
  try {
    if (movDeleteQueue.length > 0) {
      for (const id of movDeleteQueue) {
        await safeApiCall(`/api/movimentacao/${id}`, {method:'DELETE'}, 'Falha ao excluir movimentação.');
      }
      await debouncedLoad();
    }
  } catch (err) {
    alert('Erro ao processar movimentação: ' + err.message);
  }
  
  movDeleteQueue = [];
  movUndoStack = [];
  movEditando = false;
  toggleEditUiMov(false);
  
  fecharModal('ovMov');
}

async function salvarMovEFechar() {
  const v = parseVal(document.getElementById('movValor').value);
  if (v !== null && v !== 0) {
    await salvarMov();
  }
  await fecharEefetivarMov();
}

async function renomearReceita() {
  const atual = (dados.config && dados.config.receita_label) || 'Receitas';
  const novo = window.prompt('Nome da linha de receitas:', atual);
  if (!novo || novo === atual) return;
  try {
    await safeApiCall('/api/config', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({receita_label:novo.trim()})
    }, 'Falha ao renomear linha de receitas.');
    debouncedLoad();
  } catch (error) {
    console.error('Erro em renomearReceita:', error);
    alert('Erro: ' + error.message);
  }
}
