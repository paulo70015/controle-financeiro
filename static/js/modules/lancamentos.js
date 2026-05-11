function popularSel() {
  const cats = dados.categorias || [];
  document.getElementById('dC').innerHTML = cats.map(c => `<option value="${c.nome}" data-cartao="${c.is_cartao ? 1 : 0}">${c.nome}</option>`).join('');
  document.getElementById('dC').onchange = function() {
    const opt = this.options[this.selectedIndex];
    const isCartao = opt && opt.getAttribute('data-cartao') === '1';
    const container = document.getElementById('dIgnorarContainer');
    if (container) container.style.display = isCartao ? 'none' : '';
  };
  ['dM', 'rM'].forEach(id => {
    document.getElementById(id).innerHTML =
      `<option value="0">— Todos os meses —</option>` +
      MESES.map((m, i) => `<option value="${i+1}">${m}</option>`).join('');
    document.getElementById(id).value = new Date().getMonth() + 1;
  });
}

function abrirDet(mes, cat, tit) {
  const catReal = (dados && dados.categorias && cat !== '__rec__') 
    ? (dados.categorias.find(c => c.nome.trim().normalize('NFC') === cat.trim().normalize('NFC'))?.nome || cat) 
    : cat;

  detCtx = {mes, cat: catReal, tit};
  detDeleteQueue = [];
  if (typeof detUndoManager !== 'undefined') detUndoManager.clear();
  const tituloFormatado = window.formatBankIcons ? window.formatBankIcons(tit) : tit;
  document.getElementById('detT').innerHTML = tituloFormatado;
  document.getElementById('aN').placeholder = 'Nota';
  document.getElementById('aV').placeholder = 'Valor (R$)';
  if (typeof preencherMesesEdicaoDet === 'function') preencherMesesEdicaoDet();
  if (document.getElementById('detMesEditar')) document.getElementById('detMesEditar').value = String(mes);
  if (typeof toggleMesEdicaoDet === 'function') toggleMesEdicaoDet(false);

  const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
  const selStatus = document.getElementById('detStatus');
  const recSel = document.getElementById('detRecStatus');
  if (locked) {
    if (selStatus) selStatus.style.display = 'none';
    if (recSel) recSel.style.display = 'none';
  } else if (cat === '__rec__') {
    selStatus.style.display = 'none';
    if (recSel) recSel.style.display = 'block';
  } else {
    selStatus.style.display = 'block';
    if (recSel) recSel.style.display = 'none';
    const stVal = (dados.pagamentos && dados.pagamentos[cat]) ? dados.pagamentos[cat][mes] || 0 : 0;
    selStatus.value = stVal;
    selStatus.className = stVal == 1 ? 'st-sel-1' : stVal == 2 ? 'st-sel-2' : '';
  }

  if (document.getElementById('detIgnorarContainer')) {
    const catData = (dados.categorias || []).find(c => c.nome === catReal);
    const isCartao = catData ? !!catData.is_cartao : false;
    document.getElementById('detIgnorarContainer').style.display = (cat === '__rec__' || locked || isCartao) ? 'none' : 'block';
  }
  if (document.getElementById('detIgnorar')) document.getElementById('detIgnorar').checked = false;

  document.getElementById('aV').value = '';
  document.getElementById('aN').value = '';
  document.getElementById('aV').disabled = locked;
  document.getElementById('aN').disabled = locked;
  const b1 = document.querySelector('button[onclick="addLanc()"]');
  const b2 = document.querySelector('button[onclick="addLancEFechar()"]');
  if (b1) b1.style.display = locked ? 'none' : 'inline-block';
  if (b2) b2.style.display = locked ? 'none' : 'inline-block';
  carregarDetLocal();
  abrirModal('ovDet');
  setTimeout(() => document.getElementById('aV').focus(), 200);
}

async function delD(id) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  if (typeof hideUndoCsvButton === 'function') hideUndoCsvButton();
  detDeleteQueue.push({tipo:'despesa', id});
  if (typeof detUndoManager !== 'undefined') detUndoManager.push({type: 'delete', id: id});
  carregarDetLocal();
}

async function verRec(mes) {
  const tit = 'Receitas - ' + MESES[mes - 1];
  detCtx = {mes, cat:'__rec__', tit};
  detDeleteQueue = [];
  if (typeof detUndoManager !== 'undefined') detUndoManager.clear();
  const tituloFormatado = window.formatBankIcons ? window.formatBankIcons(tit) : tit;
  document.getElementById('detT').innerHTML = tituloFormatado;
  document.getElementById('aN').placeholder = 'Descrição (ex: Salário, PLR...)';
  document.getElementById('aV').placeholder = 'Valor (R$)';
  if (typeof preencherMesesEdicaoDet === 'function') preencherMesesEdicaoDet();
  if (document.getElementById('detMesEditar')) document.getElementById('detMesEditar').value = String(mes);
  if (typeof toggleMesEdicaoDet === 'function') toggleMesEdicaoDet(false);
  document.getElementById('detStatus').style.display = 'none';
  
  const locked = typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado;
  const recSel = document.getElementById('detRecStatus');
  if (recSel) {
    recSel.style.display = locked ? 'none' : 'block';
    const stVal = (dados.pagamentos && dados.pagamentos['__rec__'] && dados.pagamentos['__rec__'][mes] !== undefined) ? dados.pagamentos['__rec__'][mes] : 1;
    recSel.value = stVal === 1 ? '1' : '2';
  }
  
  document.getElementById('aV').value = '';
  document.getElementById('aN').value = '';
  document.getElementById('aV').disabled = locked;
  document.getElementById('aN').disabled = locked;
  const b1 = document.querySelector('button[onclick="addLanc()"]');
  const b2 = document.querySelector('button[onclick="addLancEFechar()"]');
  if (b1) b1.style.display = locked ? 'none' : 'inline-block';
  if (b2) b2.style.display = locked ? 'none' : 'inline-block';
  if (document.getElementById('detIgnorarContainer')) document.getElementById('detIgnorarContainer').style.display = 'none';
  carregarDetLocal();
  abrirModal('ovDet');
}

async function delR(id) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado. Desbloqueie para alterar.');
  if (typeof hideUndoCsvButton === 'function') hideUndoCsvButton();
  detDeleteQueue.push({tipo:'receita', id});
  if (typeof detUndoManager !== 'undefined') detUndoManager.push({type: 'delete', id: id});
  carregarDetLocal();
}

function abrirD() {
  document.getElementById('dV').value = '';
  document.getElementById('dN').value = '';
  if (document.getElementById('dIgnorar')) document.getElementById('dIgnorar').checked = false;
  if (document.getElementById('dC').onchange) document.getElementById('dC').onchange();
  abrirModal('ovD');
  setTimeout(() => document.getElementById('dV').focus(), 200);
}

function abrirR() {
  abrirModal('ovR');
  setTimeout(() => document.getElementById('rV').focus(), 200);
}

async function salvarD() {
  if (typeof hideUndoCsvButton === 'function') hideUndoCsvButton();
  const categoria = document.getElementById('dC').value;
  const mes = parseInt(document.getElementById('dM').value);
  const v = parseVal(document.getElementById('dV').value);
  const n = document.getElementById('dN').value;
  const ign = document.getElementById('dIgnorar') ? document.getElementById('dIgnorar').checked : false;
  if (!categoria) return alert('Selecione uma categoria');
  if (v === null && !n) return alert('Informe o valor ou a nota');

  await enviarLancamentosMeses('/api/despesa', {ano, categoria, valor: v||0, nota: n, ignorar_total: ign}, mes);
  document.getElementById('dV').value = '';
  document.getElementById('dN').value = '';
  if (document.getElementById('dIgnorar')) document.getElementById('dIgnorar').checked = false;
  fecharModal('ovD');
  debouncedLoad();
}

async function salvarR() {
  if (typeof hideUndoCsvButton === 'function') hideUndoCsvButton();
  const descricao = document.getElementById('rD').value.trim() || 'Receita';
  const mes = parseInt(document.getElementById('rM').value);
  const v = parseVal(document.getElementById('rV').value);
  const n = document.getElementById('rN').value;
  if (v === null) return alert('Informe o valor numérico');
  await enviarLancamentosMeses('/api/receita', {ano, descricao, valor: v, nota: n}, mes);
  fecharModal('ovR');
  debouncedLoad();
}

async function enviarLancamentosMeses(url, payloadBase, mesSelecionado) {
  if (mesSelecionado === 0) {
    // Otimização DRY: Aproveita o endpoint otimizado de Lote no Backend
    const isReceita = url.includes('receita');
    const loteUrl = isReceita ? '/api/receita/lote' : '/api/despesa/lote';
    const lotePayload = { ...payloadBase, acrescimo: 0 };
    delete lotePayload.mes; // Não precisamos enviar o mês pro endpoint de Lote
    await safeApiCall(loteUrl, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(lotePayload)
    }, 'Falha ao salvar em lote');
  } else {
    await safeApiCall(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ ...payloadBase, mes: mesSelecionado })
    }, 'Falha ao salvar lançamento');
  }
}
