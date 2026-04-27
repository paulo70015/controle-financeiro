var loteCtx = {};

function abrirLote(tipo, catNome = '', catId = null) {
  loteCtx = {tipo, catNome, catId};
  const isRec = tipo === 'receita';
  document.getElementById('ltTitulo').textContent = isRec ? 'Receitas em Todos os Meses' : 'Lançar em Todos os Meses';
  document.getElementById('ltSub').textContent = isRec ? 'Aplicar lançamentos em lote para o ano' : 'Categoria: ' + catNome;
  document.getElementById('ltDescRow').style.display = isRec ? 'block' : 'none';
  document.getElementById('ltD').value = isRec ? 'Receita' : '';
  document.getElementById('ltV').value = '';
  document.getElementById('ltA').value = '';
  document.getElementById('ltN').value = '';
  document.getElementById('ltPreview').style.display = 'none';
  document.getElementById('ltBtnDel').title = isRec ? 'Apagar todas as receitas do ano' : 'Apagar todos os lançamentos da categoria';
  abrirModal('ovLote');
  setTimeout(() => document.getElementById('ltV').focus(), 200);
}

function atualizarLotePreview() {
  const v = parseVal(document.getElementById('ltV').value) || 0;
  const a = parseVal(document.getElementById('ltA').value) || 0;
  const prev = document.getElementById('ltPreview');
  if (!v) {
    prev.style.display = 'none';
    return;
  }
  const linhas = MESES.map((m, i) => {
    const val = Math.round((v + a * i) * 100) / 100;
    return `<span style="display:inline-block;min-width:110px;margin:2px 4px"><b>${m.substring(0,3)}:</b> ${BRL(val)}</span>`;
  });
  prev.innerHTML = linhas.join('');
  prev.style.display = 'block';
}

async function salvarLote() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado.');

  const v = parseVal(document.getElementById('ltV').value);
  if (!v) return alert('Informe o valor base');
  const a = parseVal(document.getElementById('ltA').value) || 0;
  const n = document.getElementById('ltN').value;
  
  try {
    if (loteCtx.tipo === 'receita') {
      const desc = document.getElementById('ltD').value || 'Receita';
      await safeApiCall('/api/receita/lote', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ano, valor:v, acrescimo:a, descricao:desc, nota:n})
      });
    } else {
      await safeApiCall('/api/despesa/lote', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ano, categoria:loteCtx.catNome, valor:v, acrescimo:a, nota:n})
      });
    }
    fecharModal('ovLote');
    debouncedLoad();
  } catch (error) {
    alert('Erro ao salvar em lote: ' + error.message);
  }
}

async function apagarLote() {
  if (typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) return alert('Este ano está travado.');

  if (loteCtx.tipo === 'receita') apagarTodasReceitas();
  else if (loteCtx.catNome) apagarLinhaCat(loteCtx.catNome);
}
