﻿async function importarCSV(input) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) {
    alert('Este ano está travado. Desbloqueie para importar dados.');
    input.value = '';
    return;
  }
  const file = input.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('arquivo', file);
  input.value = '';
  try {
    const r = await fetch('/api/importar_csv', { method: 'POST', body: fd });
    const d = await r.json();
    if (d.ok) {
      if (d.undo_available) {
        sessionStorage.setItem('csvUndoAvailable', 'true');
      }
      const { despesas, movimentacoes, depositos, fixas, metas, rendimentos } = d.importados;
      const erroMsg = d.erros && d.erros.length ? '\n\u26A0 ' + d.erros.length + ' erro(s): ' + d.erros[0] : '';
      alert('\u2713 CSV importado (ano ' + d.ano + ')!\n\u2022 ' + despesas + ' despesa(s)\n\u2022 ' + movimentacoes + ' movimenta\u00e7\u00e3o(\u00f5es)\n\u2022 ' + depositos + ' dep\u00f3sito(s) em conta\n\u2022 ' + (fixas||0) + ' despesa(s) fixa(s)\n\u2022 ' + (metas||0) + ' meta(s)\n\u2022 ' + (rendimentos||0) + ' rendimento(s)' + erroMsg);
      window.location = '?ano=' + d.ano;
    } else {
      alert('Erro: ' + (d.erro || JSON.stringify(d)));
    }
  } catch(e) {
    alert('Falha na importa\u00e7\u00e3o: ' + e.message);
  }
}

function checkUndoCsvButton() {
  const btn = document.getElementById('btnUndoCsv');
  if (!btn) return;
  if (sessionStorage.getItem('csvUndoAvailable') === 'true') {
    btn.style.display = 'inline-block';
  } else {
    btn.style.display = 'none';
  }
}

function hideUndoCsvButton() {
  sessionStorage.removeItem('csvUndoAvailable');
  checkUndoCsvButton();
}

async function desfazerImportacaoCsv() {
  if (!confirm('Deseja desfazer a última importação de CSV? Todas as alterações feitas desde a importação serão perdidas.')) {
    return;
  }
  try {
    const r = await fetch('/api/csv/undo', { method: 'POST' });
    const d = await r.json();
    if (d.ok) {
      hideUndoCsvButton();
      alert('Importação desfeita com sucesso!');
      window.location.reload();
    } else {
      alert('Erro ao desfazer importação: ' + (d.erro || 'Erro desconhecido.'));
    }
  } catch (e) {
    alert('Falha na comunicação para desfazer a importação: ' + e.message);
  }
}

async function excluirCategoriaMenu(catId, nome) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) {
    alert('Este ano está travado e não pode ser alterado.');
    return;
  }
  if (!confirm('Remover a categoria "' + nome + '" e TODOS os seus lançamentos em TODOS os anos?\nEsta ação não pode ser desfeita.')) return;
  
  try {
    await fetch('/api/categoria/' + catId, { method: 'DELETE' });
    if (typeof fecharModal === 'function') fecharModal('ovRen'); // Prevenção caso o modal estivesse aberto no background
    debouncedLoad();
  } catch (error) {
    alert('Erro ao remover categoria: ' + error.message);
  }
}

async function apagarLinhaCat(cat) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) {
    alert('Este ano está travado e não pode ser alterado.');
    return;
  }
  const catReal = (dados && dados.categorias)
    ? (dados.categorias.find(c => c.nome.trim().normalize('NFC') === cat.trim().normalize('NFC'))?.nome || cat)
    : cat;

  if (!confirm('Apagar TODOS os lan\u00e7amentos de "' + catReal + '" em ' + ano + '?')) return;
  await fetch('/api/despesas/' + ano + '/' + encodeURIComponent(catReal), { method: 'DELETE' });
  if (typeof fecharModal === 'function') fecharModal('ovLote');
  debouncedLoad();
}

async function apagarTodasReceitas() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) {
    alert('Este ano está travado e não pode ser alterado.');
    return;
  }
  if (!confirm('Deseja realmente apagar TODAS as receitas lançadas no ano de ' + ano + '? Esta ação não pode ser desfeita.')) return;
  try {
    await fetch('/api/receitas/' + ano, { method: 'DELETE' });
    if (typeof fecharModal === 'function') fecharModal('ovLote');
    debouncedLoad();
  } catch (error) {
    alert('Erro ao apagar receitas: ' + error.message);
  }
}

async function removerAno(e, anoRemover) {
  e.preventDefault();
  e.stopPropagation();
  if (Number(anoRemover) === Number(ano)) {
    alert('Não é possível remover o ano que está selecionado atualmente.\nMude para outro ano nas abas acima primeiro.');
    return;
  }
  const ok = confirm(`Deseja realmente remover o ano ${anoRemover} e TODOS os seus lançamentos?\n\nEsta ação não pode ser desfeita.`);
  if (!ok) return;
  const r = await fetch(`/api/ano/${anoRemover}`, {method: 'DELETE'});
  const d = await r.json();
  if (!d.ok) return alert('Erro ao remover: ' + (d.erro || ''));
  
  let extras = JSON.parse(sessionStorage.getItem('anosExtras') || '[]');
  extras = extras.filter(a => Number(a) !== Number(anoRemover));
  sessionStorage.setItem('anosExtras', JSON.stringify(extras));
  
  // Remove visualmente do array global de anos e recarrega silenciosamente a tela
  const idx = anos_srv.findIndex(a => Number(a) === Number(anoRemover));
  if (idx > -1) anos_srv.splice(idx, 1);
  
  await debouncedLoad();
}

function adicionarAno() {
  document.getElementById('anoNovoVal').value = ano + 1;
  document.getElementById('anoNovoDuplicar').checked = false;
  document.getElementById('anoNovoDuplicarInfo').style.display = 'none';
  abrirModal('ovAno');
  setTimeout(() => document.getElementById('anoNovoVal').focus(), 100);
}

document.addEventListener('change', function(e) {
  if (e.target.id === 'anoNovoDuplicar') {
    document.getElementById('anoNovoDuplicarInfo').style.display = e.target.checked ? 'block' : 'none';
  }
});

async function confirmarNovoAno() {
  if (typeof hideUndoCsvButton === 'function') hideUndoCsvButton();
  const novoAno = parseInt(document.getElementById('anoNovoVal').value);
  if (!novoAno || isNaN(novoAno)) return alert('Informe um ano válido');
  const duplicar = document.getElementById('anoNovoDuplicar').checked;
  if (duplicar) {
    const res = await fetch('/api/duplicar_ano', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ano_origem:ano, ano_destino:novoAno}) });
    const data = await res.json();
    if (!data.ok) return alert('Erro ao duplicar: ' + (data.erro || ''));
  } else {
    // Garante que o ano fique registrado na tabela `anos` mesmo sem duplicação
    const resAno = await fetch('/api/ano', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ano: novoAno}) });
    if (!resAno.ok) {
      const errData = await resAno.json().catch(() => ({}));
      console.error('Falha ao registrar ano:', errData);
      return alert('Erro ao criar ano: ' + (errData.erro || resAno.statusText));
    }
  }
  const extras = JSON.parse(sessionStorage.getItem('anosExtras') || '[]');
  if (!extras.includes(novoAno)) extras.push(novoAno);
  sessionStorage.setItem('anosExtras', JSON.stringify(extras));
  fecharModal('ovAno');
  window.location = '?ano=' + novoAno;
}

function nomeArquivoExportacao(nomeBase, extensao) {
  const agora = new Date();
  const dd = String(agora.getDate()).padStart(2, '0');
  const mm = String(agora.getMonth() + 1).padStart(2, '0');
  const aaaa = agora.getFullYear();
  return nomeBase + '_' + dd + mm + aaaa + '.' + extensao.replace(/^\./, '');
}

function exportarCSV() {
  const url = '/api/exportar/' + ano;
  const a = document.createElement('a');
  a.href = url;
  a.download = nomeArquivoExportacao('despesas-' + ano, 'csv');
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function exportarDB() {
  const url = '/api/db/exportar';
  const a = document.createElement('a');
  a.href = url;
  a.download = nomeArquivoExportacao('controle-financeiro-bd', 'txt');
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function importarDB(input) {
  const file = input.files[0];
  if (!file) return;
  input.value = '';

  if (!confirm('Importar este TXT substituirá todos os dados atuais do banco Supabase. Deseja continuar?')) {
    return;
  }

  const fd = new FormData();
  fd.append('arquivo', file);

  try {
    const r = await fetch('/api/db/importar', { method: 'POST', body: fd });
    const d = await r.json();
    if (!d.ok) {
      alert('Erro ao importar BD: ' + (d.erro || JSON.stringify(d)));
      return;
    }

    const total = Object.values(d.importados || {}).reduce((soma, qtd) => soma + Number(qtd || 0), 0);
    alert('BD importado com sucesso!\n' + total + ' registro(s) importado(s).');
    window.location.reload();
  } catch (e) {
    alert('Falha na importação do BD: ' + e.message);
  }
}

function toggleCsvMenu() {
  const dropdown = document.getElementById('csvDropdown');
  if (dropdown) dropdown.classList.toggle('open');
}

function toggleDbMenu() {
  const dropdown = document.getElementById('dbDropdown');
  if (dropdown) dropdown.classList.toggle('open');
}
document.addEventListener('click', function(e) {
  const menus = [
    { menu: document.getElementById('csvMenu'), dropdown: document.getElementById('csvDropdown') },
    { menu: document.getElementById('dbMenu'), dropdown: document.getElementById('dbDropdown') }
  ];
  for (const item of menus) {
    if (item.menu && item.dropdown && !item.menu.contains(e.target)) {
      item.dropdown.classList.remove('open');
    }
  }
});

async function toggleTravarAno(e, anoAlvo) {
  e.preventDefault();
  e.stopPropagation();
  const acao = isAnoBloqueado ? 'desbloquear' : 'travar';
  if (!confirm(`Deseja realmente ${acao} o ano ${anoAlvo}?\n\nQuando travado, bloqueia edições, exclusões e novos lançamentos.`)) return;

  const novoValor = isAnoBloqueado ? '0' : '1';
  const chaveLock = 'ano_bloqueado_' + anoAlvo;

  try {
    const r = await fetch('/api/config', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ 
        chave: chaveLock, 
        valor: novoValor,
        [chaveLock]: novoValor 
      })
    });
    const d = await r.json();
    if (d.ok) {
      debouncedLoad();
    } else {
      alert('Erro ao alterar status do ano: ' + (d.erro || ''));
    }
  } catch (err) {
    alert('Falha na comunicação: ' + err.message);
  }
}

async function toggleStatus(catNome, mes) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return;
  const catNomeReal = dados.categorias.find(c => c.nome.replace(/[^a-zA-Z0-9]/g,'_') === catNome)?.nome || catNome;
  
  let atual;
  if (catNomeReal === '__rec__') {
    atual = (dados.pagamentos && dados.pagamentos['__rec__'] && dados.pagamentos['__rec__'][mes] !== undefined) ? dados.pagamentos['__rec__'][mes] : 1;
  } else {
    atual = (dados.pagamentos && dados.pagamentos[catNomeReal]) ? dados.pagamentos[catNomeReal][mes] || 0 : 0;
  }
  
  const proximo = catNomeReal === '__rec__' ? (atual === 1 ? 2 : 1) : (atual + 1) % 3;
  await fetch('/api/pagamento_status', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ano, mes, categoria: catNomeReal, status: proximo})
  });
  await debouncedLoad();
}

async function mudarStatusDet(val) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return;
  if (detCtx.cat === '__rec__') return;
  const status = parseInt(val);
  
  const selStatus = document.getElementById('detStatus');
  selStatus.className = status == 1 ? 'st-sel-1' : status == 2 ? 'st-sel-2' : '';

  await fetch('/api/pagamento_status', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ano, mes: detCtx.mes, categoria: detCtx.cat, status})
  });
  await debouncedLoad();
  carregarDetLocal();
}

async function mudarStatusRec(val) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return;
  const status = parseInt(val);
  await fetch('/api/pagamento_status', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ano, mes: detCtx.mes, categoria: '__rec__', status})
  });
  await debouncedLoad();
  carregarDetLocal();
}

async function marcarMesComoPago(mes, event) {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) {
    alert('Ano travado. Não é possível alterar o status de pagamento.');
    return;
  }

  const cats = dados.categorias || [];
  const fixasCtx = window.CFDomainFixas ? window.CFDomainFixas.buildFixasContext(dados.fixas || [], cats) : null;
  const categoriasParaAlterar = [];

  const stRec = (dados.pagamentos && dados.pagamentos['__rec__'] && dados.pagamentos['__rec__'][mes] !== undefined) ? dados.pagamentos['__rec__'][mes] : 1;
  categoriasParaAlterar.push({ cat: '__rec__', atual: stRec });

  for (const cat of cats) {
    const d = (dados.despesas && dados.despesas[cat.nome]) ? dados.despesas[cat.nome] : {};
    const vLanc = d[mes] ? d[mes].valor : 0;
    const notas = d[mes] ? d[mes].notas : '';
    const excKey = cat.id + '_' + mes;
    const fixaExcluida = (dados.fixas_excecoes || {})[excKey] || false;
    const totalFixasCat = fixasCtx ? fixasCtx.totalFixasDaCategoria(cat) : 0;
    const vTotal = vLanc + (!fixaExcluida ? totalFixasCat : 0);
    
    if (vTotal !== 0 || cat.inclui_fixas || notas) {
      const stVal = (dados.pagamentos && dados.pagamentos[cat.nome]) ? dados.pagamentos[cat.nome][mes] || 0 : 0;
      categoriasParaAlterar.push({ cat: cat.nome, atual: stVal });
    }
  }

  if (categoriasParaAlterar.length === 0) return;

  const todasPagas = categoriasParaAlterar.every(c => c.atual === 2);

  document.body.style.cursor = 'wait';
  const btn = event && event.target;
  let textoOriginal = '';
  if (btn) {
    textoOriginal = btn.innerHTML;
    btn.innerHTML = '&#8987;';
    btn.style.pointerEvents = 'none';
  }

  try {
    let erros = [];
    const targetCats = todasPagas ? categoriasParaAlterar : categoriasParaAlterar.filter(c => c.atual !== 2);
    const gruposPorStatus = new Map();

    for (let i = 0; i < targetCats.length; i++) {
      const item = targetCats[i];
      const statusAlvo = todasPagas ? (item.cat === '__rec__' ? 1 : 0) : 2;
      if (!gruposPorStatus.has(statusAlvo)) gruposPorStatus.set(statusAlvo, []);
      gruposPorStatus.get(statusAlvo).push(item.cat);
    }

    for (const [statusAlvo, categorias] of gruposPorStatus.entries()) {
      try {
        await safeApiCall('/api/pagamento_status/lote', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ano, mes, categorias, status: statusAlvo})
        });
      } catch (err) {
        erros.push(...categorias);
      }
    }
    await debouncedLoad();

    if (erros.length > 0) {
      alert(`Ocorreu um erro ao alterar o status de: ${erros.join(', ')}`);
    }
  } catch (e) {
    console.error(e);
    alert('Erro ao processar: ' + e.message);
    await debouncedLoad();
  } finally {
    document.body.style.cursor = 'default';
    if (btn) {
      btn.innerHTML = textoOriginal;
      btn.style.pointerEvents = 'auto';
    }
  }
}

window.apagarLinhaCat = apagarLinhaCat;
window.apagarTodasReceitas = apagarTodasReceitas;
window.excluirCategoriaMenu = excluirCategoriaMenu;
