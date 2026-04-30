﻿﻿﻿﻿﻿var rendCtx = { local_id: null, mes: null, nome: '' };
var rendProjCtx = { local_id: null, nome: '' };
var rendDeleteQueue = [];
var rendEditandoId = null;
var rendOriginalData = null;

const rendUndoManager = new UndoManager('rendBtnUndo', { get queue() { return rendDeleteQueue; }, set queue(v) { rendDeleteQueue = v; } });

function toggleEditUiRend(isEdit) {
  const b1 = document.querySelector('button[onclick="salvarRendimentoLancamento()"]');
  const b2 = document.querySelector('button[onclick="salvarRendimentoLancamentoEFechar()"]');
  if (b1) b1.textContent = isEdit ? 'Alterar' : '+ Lançar';
  if (b2) b2.textContent = isEdit ? 'Alterar e fechar' : 'Salvar e fechar';
}

function atualizarRendLancDiffUi() {
  const tipoEl = document.getElementById('rendLancTipo');
  const boxEl = document.getElementById('rendLancDiffBox');
  const diffEl = document.getElementById('rendLancDiff');
  const labelEl = document.getElementById('rendLancDiffLabel');
  if (!tipoEl || !boxEl) return;

  const isRendimento = tipoEl.value === 'rendimento';
  boxEl.style.display = isRendimento ? 'flex' : 'none';
  if (diffEl && !rendEditandoId) diffEl.checked = isRendimento;
  if (labelEl) {
    labelEl.textContent = `Usar valor final informado e lançar só a diferença em relação ao mês anterior (${BRL(obterValorAnteriorRendimentoLancamento())}).`;
  }
}
window.atualizarRendLancDiffUi = atualizarRendLancDiffUi;

function obterValorAnteriorRendimentoLancamento() {
  const localId = parseInt(document.getElementById('rendLancLocalId')?.value || rendCtx.local_id || '0');
  const mes = parseInt(document.getElementById('rendLancMes')?.value || rendCtx.mes || '0');
  if (!localId || !mes) return 0;

  const { historico } = calcularSaldoAcumuladoLocal(localId, mes);
  return historico[mes - 1]?.saldoMesAnterior || 0;
}

function obterValorRendimentoPorDiferenca(localId, mes, valorFinalInformado) {
  const { historico } = calcularSaldoAcumuladoLocal(localId, mes);
  const mesInfo = historico[mes - 1];
  if (!mesInfo) return valorFinalInformado;

  const rendimentoOriginal = rendEditandoId && rendOriginalData?.tipo === 'rendimento'
    ? parseFloat(rendOriginalData.valor || 0)
    : 0;
  const saldoAntesDoRendimento = arred2(mesInfo.saldoMesAnterior + mesInfo.aporte);
  const outrosRendimentos = arred2((mesInfo.qtdRend > 0 ? mesInfo.rendimento : 0) - rendimentoOriginal);
  return arred2(valorFinalInformado - saldoAntesDoRendimento - outrosRendimentos);
}

document.addEventListener('change', function(e) {
  if (e.target && e.target.id === 'rendLancTipo') atualizarRendLancDiffUi();
});

window.editarRend = function(id, tipo, valor, nota) {
  window.iniciarEdicaoInline({
    checkLock: true,
    onInit: () => {
      rendEditandoId = id;
      rendOriginalData = { tipo, valor, nota };
    },
    campos: [
      { id: 'rendLancTipo', valor: tipo || 'aporte' },
      { id: 'rendLancValor', valor: valor, formatar: v => (v !== undefined && v !== null && v !== '') ? parseFloat(v).toLocaleString('pt-BR', {minimumFractionDigits:2}) : '' },
      { id: 'rendLancNota', valor: nota }
    ],
    toggleFn: isEdit => toggleEditUiRend(isEdit),
    focusId: 'rendLancValor'
  });
  const diffEl = document.getElementById('rendLancDiff');
  if (diffEl) diffEl.checked = false;
  atualizarRendLancDiffUi();
};

function arred2(v) {
  return Math.round((parseFloat(v) || 0) * 100) / 100;
}

function obterLancamentosLocalRendimento(localId) {
  return (dados.rendimentos || {})[String(localId)] || {};
}

function calcularSaldoAcumuladoLocal(localId, ateOMes = 12, lancamentosAdicionais = null) {
  const localLancs = obterLancamentosLocalRendimento(localId);
  const local = (dados.rendimentos_locais || []).find(l => l.id === localId);
  const taxaProjecao = (local?.projecao_taxa || 0) / 100;
  
  let saldo = 0;
  const historico = [];
  
  for (let m = 1; m <= ateOMes; m++) {
    const info = localLancs[m] || {};
    let aporte = parseFloat(info.aporte || 0);
    let rendimentoReal = parseFloat(info.rendimento || 0);
    let qtdRend = info.qtd_rendimentos || 0;
    
    // Correção: Substituir (em vez de somar) os dados cacheados pelos dados da fila local
    if (m === ateOMes && lancamentosAdicionais !== null) {
      aporte = lancamentosAdicionais.reduce((s, r) => s + (r.tipo === 'aporte' ? r.valor : 0), 0);
      const rendAdicionais = lancamentosAdicionais.filter(r => r.tipo === 'rendimento');
      qtdRend = rendAdicionais.length;
      rendimentoReal = rendAdicionais.reduce((s, r) => s + r.valor, 0);
    }
    
    const saldoMesAnterior = saldo;
    saldo = arred2(saldo + aporte);
    
    let rendimentoDoMes = rendimentoReal;
    let isProjecao = false;
    
    if (qtdRend === 0 && taxaProjecao > 0 && saldo > 0) {
      rendimentoDoMes = arred2(saldo * taxaProjecao);
      isProjecao = true;
    }
    
    saldo = arred2(saldo + rendimentoDoMes);
    
    historico.push({ 
      mes: m, 
      saldo, 
      saldoMesAnterior,
      aporte, 
      rendimento: rendimentoDoMes, 
      isProjecao,
      qtdRend
    });
  }
  
  return { saldo, historico, taxaProjecao };
}

function calcularProjecoesRendimento(localId, percentual) {
  const taxaDecimal = (parseFloat(percentual) || 0) / 100;
  const { historico } = calcularSaldoAcumuladoLocal(localId, 12);
  
  const projecoes = [];
  historico.forEach(h => {
    if (h.qtdRend === 0 && h.isProjecao && taxaDecimal > 0) {
      projecoes.push({ 
        mes: h.mes, 
        valor: h.rendimento, 
        saldo_base: h.saldoMesAnterior + h.aporte 
      });
    }
  });
  
  return projecoes;
}

function renderRendimentos() {
  const tw = document.getElementById('tw');
  if (!tw) return;

  const _fixedWrap = document.getElementById('fixedWrap');
  if (_fixedWrap) _fixedWrap.remove();
  if (tw._thObserver) {
    tw._thObserver.disconnect();
    delete tw._thObserver;
  }
  tw.style.maxHeight = '';
  tw.style.overflowY = '';
  tw.removeAttribute('data-scroll');

  const locais = dados.rendimentos_locais || [];
  const lancs = dados.rendimentos || {};

  const th = (txt, cls='') => `<th${cls?' class="'+cls+'"':''}>${txt}</th>`;
  let h = '<table><thead><tr>' + th('Local', 'cat');
  MESES_ABREV.forEach(m => h += th(m));
  h += '</tr></thead><tbody>';

  const totaisAporteMes = Array(13).fill(0);
  const totaisRendimentoMes = Array(13).fill(0);

  locais.forEach(local => {
    const localLancs = lancs[String(local.id)] || {};
    const nomeSafe = (local.nome || '').replace(/'/g, "\\'");
    const percStr = local.projecao_taxa ? String(local.projecao_taxa).replace('.', ',') + '%' : '';
    const nomeFormatado = window.formatBankIcons ? window.formatBankIcons(local.nome) : local.nome;
    
    const { historico } = calcularSaldoAcumuladoLocal(local.id, 12);

    const linksLocal = `
      <a href="#" onclick="event.preventDefault(); abrirRendimentoProjecao(${local.id},'${nomeSafe}')">&#10532; Projetar rendimentos</a>
      <a href="#" onclick="event.preventDefault(); abrirRendimentoLoteLocal(${local.id})">&#8862; Lançar em todos os meses</a>
      <a href="#" onclick="event.preventDefault(); editarRendimentoLocal(${local.id},'${nomeSafe}')">&#9998; Editar local</a>
      <a href="#" class="text-danger" onclick="event.preventDefault(); apagarLancamentosRendimentoLocal(${local.id},'${nomeSafe}')">&#10005; Apagar lançamentos</a>`;
    h += `<tr draggable="true" data-local-id="${local.id}" class="cat-row" ondragstart="dragLocalStart(event,${local.id})" ondragover="dragLocalOver(event)" ondragleave="dragLocalLeave(event)" ondrop="dropLocal(event,${local.id})"><td class="cat-nome"><div class="cc"><span title="${local.nome}">${nomeFormatado}</span>${window.buildKebabMenuHtml(linksLocal, true)}</div></td>`;

    for (let m = 1; m <= 12; m++) {
      const h_mes = historico[m - 1];
      const saldoLocal = h_mes.saldo;
      const aporte = h_mes.aporte;
      const rendimentoDoMes = h_mes.rendimento;
      const isProjecao = h_mes.isProjecao;
      const saldoMesAnterior = h_mes.saldoMesAnterior;

      totaisAporteMes[m] += aporte;
      totaisRendimentoMes[m] += rendimentoDoMes;

      if (saldoLocal !== 0 || aporte !== 0 || rendimentoDoMes !== 0) {
        const linhasRend = [
          { valor: aporte, texto: 'Aportes do mês' }
        ];
        let txtRend = 'Rendimentos do mês';
        if (isProjecao) {
          txtRend += ` (Projetado: ${percStr})`;
        } else if (rendimentoDoMes !== 0 && saldoMesAnterior > 0) {
          const pct = ((rendimentoDoMes / saldoMesAnterior) * 100).toFixed(2).replace('.', ',');
          txtRend += ` (${pct}%)`;
        }
        linhasRend.push({ valor: rendimentoDoMes, texto: txtRend });
        linhasRend.push({ valor: saldoLocal, texto: 'Saldo acumulado' });

        let tit = `${local.nome} - ${MESES[m - 1]}`;
        if (window.formatarLinhasTooltip) {
          const txtFormatado = window.formatarLinhasTooltip(linhasRend);
          if (txtFormatado) tit += '\n' + txtFormatado;
        } else {
          tit += `\nAportes do mês: ${BRL(aporte)}\nRendimentos do mês: ${BRL(rendimentoDoMes)}\nSaldo acumulado: ${BRL(saldoLocal)}`;
        }

        const cellClass = isProjecao ? 'rend-projecao' : '';
        h += `<td class="rend-cell ${cellClass}" title="${tit}" onmouseenter="carregarTooltipRendimentos(this, ${local.id}, ${m})" onclick="abrirRendimentoLanc(${local.id},'${nomeSafe}',${m})">${BRL(saldoLocal)}</td>`;
      } else {
        h += `<td class="rend-cell" onclick="abrirRendimentoLanc(${local.id},'${nomeSafe}',${m})"><div class="rend-vazio">+</div></td>`;
      }
    }

    h += '</tr>';
  });

  h += '<tr class="tr-rend-aportes"><td class="cat-nome"><div class="cc"><span>Aportes</span></div></td>';
  let saldoAcumuladoAportes = 0;
  for (let m = 1; m <= 12; m++) {
    saldoAcumuladoAportes += totaisAporteMes[m];
    let tit = '';
    if (window.formatarLinhasTooltip) {
      tit = window.formatarLinhasTooltip([
        { valor: totaisAporteMes[m], texto: 'Total aportado no mês' },
        { valor: saldoAcumuladoAportes, texto: 'Total acumulado de aportes' }
      ]);
    } else {
      tit = `Total aportado no mês: ${BRL(totaisAporteMes[m])}\nTotal acumulado de aportes: ${BRL(saldoAcumuladoAportes)}`;
    }
    h += `<td class="td-num" title="${tit}">${totaisAporteMes[m] ? BRL(totaisAporteMes[m]) : ''}</td>`;
  }
  h += '</tr>';

  h += '<tr class="tr-rend-rendimentos"><td class="cat-nome"><div class="cc"><span>Rendimentos</span></div></td>';
  let saldoAcumuladoRendimentos = 0;
  for (let m = 1; m <= 12; m++) {
    saldoAcumuladoRendimentos += totaisRendimentoMes[m];
    let tit = '';
    if (window.formatarLinhasTooltip) {
      tit = window.formatarLinhasTooltip([
        { valor: totaisRendimentoMes[m], texto: 'Total de rendimentos no mês' },
        { valor: saldoAcumuladoRendimentos, texto: 'Total acumulado de rendimentos' }
      ]);
    } else {
      tit = `Total de rendimentos no mês: ${BRL(totaisRendimentoMes[m])}\nTotal acumulado de rendimentos: ${BRL(saldoAcumuladoRendimentos)}`;
    }
    h += `<td class="td-num" title="${tit}">${totaisRendimentoMes[m] ? BRL(totaisRendimentoMes[m]) : ''}</td>`;
  }
  h += '</tr>';

  h += '<tr class="tr-rend-total"><td class="cat-nome"><div class="cc"><span>Saldo acumulado</span></div></td>';
  let saldoAcumuladoTotal = 0;
  for (let m = 1; m <= 12; m++) {
    saldoAcumuladoTotal += totaisAporteMes[m] + totaisRendimentoMes[m];
    let tit = '';
    if (window.formatarLinhasTooltip) {
      tit = window.formatarLinhasTooltip([
        { valor: saldoAcumuladoTotal, texto: 'Saldo total no fim do mês' }
      ]);
    } else {
      tit = `Saldo total no fim do mês: ${BRL(saldoAcumuladoTotal)}`;
    }
    h += `<td class="td-num" title="${tit}">${saldoAcumuladoTotal ? BRL(saldoAcumuladoTotal) : ''}</td>`;
  }
  h += '</tr>';

  if (!locais.length) {
    h += '<tr><td colspan="13" style="padding:16px;text-align:center;color:var(--text-muted)">Nenhum local cadastrado. Use o botão <strong>+ Local</strong>.</td></tr>';
  }

  h += '</tbody></table>';
  tw.innerHTML = h;
  if(window.CF_AplicarResize) window.CF_AplicarResize();
}

function abrirRendimentoAdd() {
  const locais = dados.rendimentos_locais || [];
  if (!locais.length) {
    alert('Cadastre ao menos um local antes de lançar.');
    abrirRendimentoLocal();
    return;
  }

  const selLocal = document.getElementById('rendAddLocal');
  const selMes = document.getElementById('rendAddMes');
  selLocal.innerHTML = locais.map(l => `<option value="${l.id}">${l.nome}</option>`).join('');
  selMes.innerHTML =
    `<option value="0">— Todos os meses —</option>` +
    MESES.map((m, i) => `<option value="${i + 1}">${m}</option>`).join('');

  selMes.value = String(new Date().getMonth() + 1);
  document.getElementById('rendAddTipo').value = 'rendimento';
  document.getElementById('rendAddValor').value = '';
  document.getElementById('rendAddNota').value = '';
  abrirModal('ovRendAdd');
  setTimeout(() => document.getElementById('rendAddValor').focus(), 120);
}

function abrirRendimentoLoteLocal(localId) {
  abrirRendimentoAdd();
  setTimeout(() => {
    const selLocal = document.getElementById('rendAddLocal');
    const selMes = document.getElementById('rendAddMes');
    if (selLocal) selLocal.value = String(localId);
    if (selMes) selMes.value = '0';
  }, 20);
}

function abrirRendimentoProjecao(localId, nome) {
  rendProjCtx = { local_id: localId, nome: nome || '' };
  const local = (dados.rendimentos_locais || []).find(l => l.id === localId);
  const taxaAtual = local ? local.projecao_taxa : null;

  document.getElementById('rendProjLocalId').value = localId;
  document.getElementById('rendProjSub').textContent = (nome || 'Local') + ' - lançamento percentual de rendimento em todos os meses';
  document.getElementById('rendProjPct').value = taxaAtual ? String(taxaAtual).replace('.', ',') : '1,00';
  abrirModal('ovRendProj');
  atualizarPreviewRendimentoProjecao();
  setTimeout(() => document.getElementById('rendProjPct').select(), 120);
}

function atualizarPreviewRendimentoProjecao() {
  const localId = parseInt(document.getElementById('rendProjLocalId').value || '0');
  const preview = document.getElementById('rendProjPreview');
  if (!localId || !preview) return;

  const percentual = parseVal(document.getElementById('rendProjPct').value);
  if (percentual === null || percentual <= 0) {
    preview.style.display = 'block';
    preview.innerHTML = 'Informe um percentual maior que zero para ver a projeção.';
    return;
  }

  const projecoes = calcularProjecoesRendimento(localId, percentual);
  if (!projecoes.length) {
    preview.style.display = 'block';
    preview.innerHTML = 'Nenhum mês com saldo suficiente para projetar.';
    return;
  }

  preview.style.display = 'block';
  preview.innerHTML = projecoes.map(item =>
    `<div>${MESES[item.mes - 1]}: ${BRL(item.valor)} sobre saldo de ${BRL(item.saldo_base)}</div>`
  ).join('');
}

async function salvarRendimentoAdd() {
  const local_id = parseInt(document.getElementById('rendAddLocal').value || '0');
  const tipo = document.getElementById('rendAddTipo').value;
  const mes = parseInt(document.getElementById('rendAddMes').value || '0');
  const valor = parseVal(document.getElementById('rendAddValor').value);
  const nota = (document.getElementById('rendAddNota').value || '').trim();

  if (!local_id) return alert('Selecione o local');
  if (valor === null && !nota) return alert('Informe valor ou nota');

  try {
    if (mes === 0) {
      await safeApiCall('/api/rendimento/lancamento/lote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ano, mes_inicio: 1, local_id, tipo, valor: valor || 0, nota }),
      }, 'Falha ao salvar em lote');
    } else {
      await safeApiCall('/api/rendimento/lancamento', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ano, mes, local_id, tipo, valor: valor || 0, nota }),
      }, 'Falha ao salvar');
    }
    fecharModal('ovRendAdd');
    await debouncedLoad();
    setView('rendimentos', false);
  } catch (error) {
    alert('Erro: ' + error.message);
  }
}

let draggedLocalId = null;

window.dragLocalStart = function(e, id) {
  draggedLocalId = id;
  e.dataTransfer.effectAllowed = 'move';
  e.currentTarget.classList.add('dragging');
};

window.dragLocalOver = function(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const tr = e.currentTarget;
  if (tr && tr.tagName === 'TR') tr.classList.add('drag-over');
};

window.dragLocalLeave = function(e) {
  const tr = e.currentTarget;
  if (tr && tr.tagName === 'TR') tr.classList.remove('drag-over');
};

window.dropLocal = async function(e, targetId) {
  e.preventDefault();
  const tr = e.currentTarget;
  if (tr && tr.tagName === 'TR') tr.classList.remove('drag-over');
  
  if (!draggedLocalId || draggedLocalId === targetId) return;

  const locaisIds = dados.rendimentos_locais.map(l => l.id);
  const fromIndex = locaisIds.indexOf(draggedLocalId);
  const toIndex = locaisIds.indexOf(targetId);

  locaisIds.splice(fromIndex, 1);
  locaisIds.splice(toIndex, 0, draggedLocalId);

  try {
    await safeApiCall('/api/rendimentos/locais/reordenar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ordem_ids: locaisIds })
    });
    await debouncedLoad(); // Recarrega os dados e re-renderiza
  } catch (err) {
    alert('Erro ao reordenar locais: ' + err.message);
  }
};

window.carregarTooltipRendimentos = debounce(async function(el, localId, mes) {
  if (el.dataset.tooltipLoaded) return;
  
  const cacheKey = `rend_${localId}_${mes}`;
  if (tooltipCache.has(cacheKey)) {
    const cachedTit = tooltipCache.get(cacheKey);
    const currentTit = el.getAttribute('title') || '';
    if (!currentTit.includes('Última alteração')) {
      el.setAttribute('title', currentTit + cachedTit);
    }
    el.dataset.tooltipLoaded = 'true';
    return;
  }
  
  el.dataset.tooltipLoaded = 'true';
  
  try {
    const r = await fetch(`/api/rendimentos_detalhe/${ano}/${mes}/${localId}?_=${Date.now()}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });
    const rows = await r.json();
    if (rows && rows.length > 0) {
      let maxMod = null;
      let maxTime = 0;
      rows.forEach(r => {
        // Correção de conflito de variáveis e remoção de datas dinâmicas da API
        const dt = r.data_alteracao || r.created_at || r.data_criacao;
        if (dt) {
          const t = new Date(dt.replace(' ', 'T') + 'Z').getTime();
          if (t && t > maxTime) { maxTime = t; maxMod = dt; }
          else if (!maxTime && (!maxMod || dt > maxMod)) maxMod = dt;
        }
      });
      if (maxMod) {
        const currentTit = el.getAttribute('title') || '';
        const tooltipSuffix = `\n\nÚltima alteração: ${formatarDataHoraBR(maxMod)}`;
        if (!currentTit.includes('Última alteração')) {
          tooltipCache.set(cacheKey, tooltipSuffix);
          el.setAttribute('title', currentTit + tooltipSuffix);
        }
      }
    }
  } catch(e) { console.error('Erro ao carregar tooltip rendimento', e); }
}, 300);

async function salvarRendimentoProjecao() {
  const local_id = parseInt(document.getElementById('rendProjLocalId').value || '0');
  const percentual = parseVal(document.getElementById('rendProjPct').value);
  if (!local_id) return alert('Local inválido');

  try {
    if (percentual === null || percentual <= 0) {
      if (!confirm('Deseja limpar a projeção de rendimentos para este local?')) return;
      await safeApiCall('/api/rendimento/projecao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ local_id, taxa: null }),
      }, 'Falha ao limpar projeção.');
    } else {
      await safeApiCall('/api/rendimento/projecao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ local_id, taxa: percentual }),
      }, 'Falha ao salvar projeção.');
    }
    fecharModal('ovRendProj');
    await debouncedLoad();
    setView('rendimentos', false);
  } catch (error) {
    alert('Erro: ' + error.message);
  }
}

async function apagarLancamentosRendimentoLocal(localId, nome) {
  const localNome = (nome || 'este local').trim();
  if (!localId) return;
  if (!confirm('Apagar todos os lançamentos de "' + localNome + '" neste ano?')) return;

  try {
    await safeApiCall('/api/rendimentos/' + ano + '/' + localId, { method: 'DELETE' }, 'Falha ao apagar lançamentos');
    await debouncedLoad();
    setView('rendimentos', false);
  } catch (error) {
    alert('Erro: ' + error.message);
  }
}

function abrirRendimentoLocal() {
  document.getElementById('rendLocalId').value = '';
  document.getElementById('rendLocalNome').value = '';
  document.getElementById('rendLocalDelBtn').style.display = 'none';
  abrirModal('ovRendLocal');
  setTimeout(() => document.getElementById('rendLocalNome').focus(), 120);
}

function editarRendimentoLocal(id, nome) {
  document.getElementById('rendLocalId').value = id;
  document.getElementById('rendLocalNome').value = nome || '';
  document.getElementById('rendLocalDelBtn').style.display = 'inline-block';
  abrirModal('ovRendLocal');
  setTimeout(() => document.getElementById('rendLocalNome').focus(), 120);
}

async function salvarRendimentoLocal() {
  const id = parseInt(document.getElementById('rendLocalId').value || '0');
  const nome = (document.getElementById('rendLocalNome').value || '').trim();
  if (!nome) return alert('Informe o nome do local');

  const url = id ? '/api/rendimento/local/' + id : '/api/rendimento/local';
  const method = id ? 'PUT' : 'POST';
  try {
    await safeApiCall(url, {
      method,
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ano, nome})
    }, 'Falha ao salvar local');
    fecharModal('ovRendLocal');
    await debouncedLoad();
    setView('rendimentos', false);
  } catch (error) {
    alert('Erro: ' + error.message);
  }
}

async function excluirRendimentoLocal() {
  const id = parseInt(document.getElementById('rendLocalId').value || '0');
  const nome = (document.getElementById('rendLocalNome').value || '').trim() || 'este local';
  if (!id) return;
  if (!confirm('Excluir "' + nome + '" e todos os seus lançamentos deste ano?')) return;
  try {
    await safeApiCall('/api/rendimento/local/' + id, {method:'DELETE'}, 'Falha ao excluir local');
    fecharModal('ovRendLocal');
    await debouncedLoad();
    setView('rendimentos', false);
  } catch (error) {
    alert('Erro: ' + error.message);
  }
}

function recalcularProjecaoModal(visiveis) {
  const { local_id, mes } = rendCtx;
  const local = (dados.rendimentos_locais || []).find(l => l.id === local_id);
  if (!local) return;

  const percStr = local.projecao_taxa ? String(local.projecao_taxa).replace('.', ',') + '%' : '';
  
  const { historico, taxaProjecao } = calcularSaldoAcumuladoLocal(local_id, mes, visiveis);
  const h_mes = historico[mes - 1];
  
  const qtdRendMes = visiveis.filter(r => r.tipo === 'rendimento').length;
  const projecaoCancelada = visiveis.find(r => r.tipo === 'rendimento' && r.valor === 0 && r.nota === 'Projeção cancelada');
  let valorProjetado = null;

  if (qtdRendMes === 0 && taxaProjecao > 0 && h_mes.saldo > 0) {
    valorProjetado = h_mes.rendimento;
  }

  const projInfoEl = document.getElementById('rendLancProjecaoInfo');
  if (projInfoEl) {
    if (projecaoCancelada) {
      // Mostrar opção de reativar projeção
      projInfoEl.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span>Projeção cancelada para este mês</span>
          <button class="btn bs" onclick="reativarProjecaoMes()" title="Reativar projeção deste mês" style="background:var(--verde); color:white;">Reativar</button>
        </div>
        <div style="margin-top:4px; font-size:11px; opacity:0.8;">Clique em "Reativar" para restaurar a projeção automática.</div>
      `;
      projInfoEl.style.display = 'block';
    } else if (valorProjetado !== null && valorProjetado > 0) {
      projInfoEl.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span>Rendimento projetado (${percStr}): <strong style="color:var(--verde)">${BRL(valorProjetado)}</strong></span>
          <button class="btn-delete" onclick="removerProjecaoMes()" title="Remover projeção deste mês">&#10005;</button>
        </div>
        <div style="margin-top:4px; font-size:11px; opacity:0.8;">Qualquer lançamento de rendimento irá substituir esta projeção.</div>
      `;
      projInfoEl.style.display = 'block';
    } else {
      projInfoEl.style.display = 'none';
    }
  }
}

async function abrirRendimentoLanc(localId, localNome, mes) {
  const tit = localNome + ' - ' + MESES[mes - 1];
  rendCtx = { local_id: localId, mes, nome: localNome, tit };
  rendDeleteQueue = [];
  rendUndoManager.clear();
  document.getElementById('rendLancLocalId').value = localId;
  document.getElementById('rendLancMes').value = mes;
  document.getElementById('rendLancTit').textContent = tit;
  const tituloFormatado = window.formatBankIcons ? window.formatBankIcons(tit) : tit;
  document.getElementById('rendLancTit').innerHTML = tituloFormatado;
  const tipoEl = document.getElementById('rendLancTipo');
  if (!tipoEl) return;
  tipoEl.value = 'aporte';
  document.getElementById('rendLancValor').value = '';
  document.getElementById('rendLancNota').value = '';
  const diffEl = document.getElementById('rendLancDiff');
  if (diffEl) diffEl.checked = true;
  atualizarRendLancDiffUi();

  const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
  tipoEl.disabled = locked;
  document.getElementById('rendLancValor').disabled = locked;
  document.getElementById('rendLancNota').disabled = locked;
  if (diffEl) diffEl.disabled = locked;
  const b1 = document.querySelector('button[onclick="salvarRendimentoLancamento()"]');
  const b2 = document.querySelector('button[onclick="salvarRendimentoLancamentoEFechar()"]');
  if (b1) b1.style.display = locked ? 'none' : 'inline-block';
  if (b2) b2.style.display = locked ? 'none' : 'inline-block';

  let projInfoEl = document.getElementById('rendLancProjecaoInfo');
  const headerEl = document.getElementById('rendLancHeader');
  if (!projInfoEl && headerEl) {
      projInfoEl = document.createElement('div');
      projInfoEl.id = 'rendLancProjecaoInfo';
      projInfoEl.style.cssText = 'display:none; background:var(--bg-linha-total-contas); color:var(--azul); border-radius:6px; padding:8px 10px; font-size:12px; margin-bottom:10px;';
      headerEl.parentNode.insertBefore(projInfoEl, headerEl.nextSibling);
  }
  if (projInfoEl) projInfoEl.style.display = 'none';

  const undoBtn = document.getElementById('rendBtnUndo');
  if (undoBtn) undoBtn.style.display = 'none';
  rendEditandoId = null;
  toggleEditUiRend(false);

  abrirModal('ovRendLanc');
  await carregarRendimentoDetalhe();
  setTimeout(() => document.getElementById('rendLancValor').focus(), 120);
}

async function desfazerRend() {
  await rendUndoManager.undo(async () => { await debouncedLoad(); setView('rendimentos', false); }, carregarRendimentoDetalhe);
}

async function carregarRendimentoDetalhe() {
  const { local_id, mes } = rendCtx || {};
  const el = document.getElementById('rendLancLista');
  if (!local_id || !mes || !el) return;

  try {
    const response = await safeApiCall('/api/rendimentos_detalhe/' + ano + '/' + mes + '/' + local_id + '?_=' + Date.now(), {}, 'Falha ao carregar');
    const rows = await response.json();
    
    const visiveis = rows.filter(r => !rendDeleteQueue.includes(r.id));
    recalcularProjecaoModal(visiveis);

    const total = visiveis.reduce((s, r) => s + (r.valor || 0), 0);
    document.getElementById('rendLancTit').innerHTML = `${rendCtx.tit || ''} <span style="font-size:13px; font-weight:bold; color:var(--azul); background:var(--bg-linha-total-contas); padding:3px 8px; border-radius:12px; margin-left:6px; vertical-align:middle">${BRL(total)}</span>`;
    const tituloFormatado = window.formatBankIcons ? window.formatBankIcons(rendCtx.tit || '') : (rendCtx.tit || '');
    document.getElementById('rendLancTit').innerHTML = `${tituloFormatado} <span style="font-size:13px; font-weight:bold; color:var(--azul); background:var(--bg-linha-total-contas); padding:3px 8px; border-radius:12px; margin-left:6px; vertical-align:middle">${BRL(total)}</span>`;

    if (!visiveis.length) {
      el.innerHTML = '<p class="empty-state">Nenhum lançamento.</p>';
      return;
    }

    el.innerHTML = visiveis.map(row => {
      const tipoTxt = row.tipo === 'aporte' ? 'Aporte' : 'Rendimento';
      const tipoColor = row.tipo === 'aporte' ? 'var(--azul)' : 'var(--verde)';
      const notaEscaped = (row.nota || '').replace(/'/g, "\\'").replace(/"/g, "&quot;");
      const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
      return buildRowDetalheHtml(`${tipoTxt}: ${BRL(row.valor || 0)}`, tipoColor, row.nota, locked ? '' : `excluirRendimentoLancamento(${row.id})`, locked ? '' : `editarRend(${row.id}, '${row.tipo}', ${row.valor}, '${notaEscaped}')`);
    }).join('');
  } catch (error) {
    el.innerHTML = `<p style="color:var(--vermelho);font-size:12px;padding:6px 0">Erro: ${error.message}</p>`;
  }
}

async function salvarRendimentoLancamento() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  const local_id = parseInt(document.getElementById('rendLancLocalId').value || '0');
  const mes = parseInt(document.getElementById('rendLancMes').value || '0');
  const tipo = document.getElementById('rendLancTipo').value;
  const valor = parseVal(document.getElementById('rendLancValor').value);
  const nota = (document.getElementById('rendLancNota').value || '').trim();
  const diffEl = document.getElementById('rendLancDiff');
  if (!local_id || !mes) {
    alert('Local/mês inválido');
    return false;
  }
  if (valor === null && !nota && rendDeleteQueue.length === 0) {
      alert('Informe valor ou nota');
      return false;
  }

  try {
    if (valor !== null || nota) {
      const valorLancamento = tipo === 'rendimento' && valor !== null && diffEl?.checked
        ? obterValorRendimentoPorDiferenca(local_id, mes, valor)
        : valor;
      const url = rendEditandoId ? '/api/rendimento/lancamento/' + rendEditandoId : '/api/rendimento/lancamento';
      const method = rendEditandoId ? 'PUT' : 'POST';
      const body = rendEditandoId 
          ? { tipo, valor: valorLancamento || 0, nota }
          : { ano, mes, local_id, tipo, valor: valorLancamento || 0, nota };
          
      await safeApiCall(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) }, 'Falha ao salvar');
      if (rendEditandoId) {
        rendUndoManager.push({ type: 'edit', url, oldBody: rendOriginalData });
      }
    }
    rendEditandoId = null;
    toggleEditUiRend(false);

    for (const id of rendDeleteQueue) {
      await fetch('/api/rendimento/lancamento/' + id, {method: 'DELETE'});
    }
    rendDeleteQueue = [];
    rendUndoManager.clear();

    document.getElementById('rendLancValor').value = '';
    document.getElementById('rendLancNota').value = '';
    if (diffEl && !rendEditandoId) diffEl.checked = tipo === 'rendimento';
    await debouncedLoad();
    setView('rendimentos', false);
    await carregarRendimentoDetalhe();
    return true;
  } catch (error) {
    alert('Erro: ' + error.message);
    return false;
  }
}

async function salvarRendimentoLancamentoEFechar() {
  const valor = parseVal(document.getElementById('rendLancValor').value);
  const nota = (document.getElementById('rendLancNota').value || '').trim();

  if (valor !== null || nota || rendDeleteQueue.length > 0) {
    const ok = await salvarRendimentoLancamento();
    if (ok) fecharModal('ovRendLanc');
  } else {
    fecharModal('ovRendLanc');
  }
}

async function fecharEefetivarRend() {
  if (rendDeleteQueue.length > 0) {
    for (const id of rendDeleteQueue) {
      await fetch('/api/rendimento/lancamento/' + id, {method: 'DELETE'});
    }
    rendDeleteQueue = [];
    rendUndoManager.clear();
    await debouncedLoad();
  }
  rendEditandoId = null;
  toggleEditUiRend(false);
  fecharModal('ovRendLanc');
}

function excluirRendimentoLancamento(lancamentoId) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado.');
  rendDeleteQueue.push(lancamentoId);
  rendUndoManager.push({type: 'delete', id: lancamentoId});
  carregarRendimentoDetalhe();
}

async function reativarProjecaoMes() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  const { local_id, mes } = rendCtx || {};
  if (!local_id || !mes) return;

  try {
    // Buscar e excluir o lançamento de "Projeção cancelada"
    const response = await safeApiCall('/api/rendimentos_detalhe/' + ano + '/' + mes + '/' + local_id + '?_=' + Date.now(), {}, 'Falha ao carregar');
    const rows = await response.json();
    
    const projecaoCancelada = rows.find(r => r.tipo === 'rendimento' && r.valor === 0 && r.nota === 'Projeção cancelada');
    if (projecaoCancelada) {
      await fetch('/api/rendimento/lancamento/' + projecaoCancelada.id, {method: 'DELETE'});
      
      rendUndoManager.push({
        type: 'reactivate_projection',
        id: projecaoCancelada.id,
        local_id,
        mes,
        ano
      });
      
      await debouncedLoad();
      setView('rendimentos', false);
      await carregarRendimentoDetalhe();
    }
  } catch (error) {
    alert('Erro: ' + error.message);
  }
}

async function removerProjecaoMes() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  const { local_id, mes } = rendCtx || {};
  if (!local_id || !mes) return;

  try {
    const response = await safeApiCall('/api/rendimento/lancamento', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ano, mes, local_id, tipo: 'rendimento', valor: 0, nota: 'Projeção cancelada' })
    }, 'Falha ao remover projeção');

    const responseData = await response.json();
    if (responseData.ok && responseData.id) {
      rendUndoManager.push({
        type: 'remove_projection',
        id: responseData.id,
        local_id,
        mes,
        ano
      });
    }

    for (const id of rendDeleteQueue) {
      await fetch('/api/rendimento/lancamento/' + id, {method: 'DELETE'});
    }
    rendDeleteQueue = [];

    await debouncedLoad();
    setView('rendimentos', false);
    await carregarRendimentoDetalhe();
  } catch (error) {
    alert('Erro: ' + error.message);
  }
}
