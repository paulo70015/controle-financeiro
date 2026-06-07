function buildCellStatusUI(catChave, mes, dados) {
  if (catChave === '__rec__') {
    const stVal = (dados.pagamentos && dados.pagamentos['__rec__'] && dados.pagamentos['__rec__'][mes] !== undefined) ? dados.pagamentos['__rec__'][mes] : 1;
    const isRealizado = stVal !== 1;
    return {
      val: stVal,
      iconTxt: isRealizado ? '✔' : '⏱',
      stClass: isRealizado ? 'st-2' : 'st-1',
      pgClass: isRealizado ? 'pg-2' : 'pg-1',
      stTip: isRealizado ? 'Realizado' : 'Previsto'
    };
  }

  const stVal = (dados.pagamentos && dados.pagamentos[catChave]) ? dados.pagamentos[catChave][mes] || 0 : 0;
  return {
    val: stVal,
    iconTxt: stVal === 1 ? '⏱' : stVal === 2 ? '✔' : '·',
    stClass: stVal > 0 ? `st-${stVal}` : '',
    pgClass: stVal > 0 ? `pg-${stVal}` : '',
    stTip: stVal === 0 ? 'Clique: Agendado' : stVal === 1 ? 'Clique: Pago' : 'Clique: Em aberto'
  };
}

function renderTabela(){
  if (typeof viewAtiva !== 'undefined' && viewAtiva === 'rendimentos') {
    if (typeof renderRendimentos === 'function') renderRendimentos();
    return;
  }
  const tw = document.getElementById('tw');

  const _fixedWrap = document.getElementById('fixedWrap');
  if (_fixedWrap) _fixedWrap.remove();
  const velhoFixed = document.getElementById('tabelaFixed');
  if (velhoFixed) velhoFixed.remove();
  if (tw) {
    if (tw._thObserver) {
      tw._thObserver.disconnect();
      delete tw._thObserver;
    }
    tw.style.maxHeight = '';
    tw.style.overflowY = '';
    tw.removeAttribute('data-scroll');
    const cg = tw.querySelector('table > colgroup');
    if (cg) cg.remove();
  }
  const movimentacoes=dados.movimentacoes||{};
  const {categorias:cats,despesas:desp,receitas:rec}=dados;
  const th = (txt, cls='') => `<th${cls?' class="'+cls+'"':''}>${txt}</th>`;
  let h='<table><thead><tr>' + th('Categoria', 'cat');
  MESES_ABREV.forEach((m, i) => {
    h += th(`<span class="mes-check" onclick="event.stopPropagation(); marcarMesComoPago(${i+1}, event)" title="Alternar status de pagamento (Pagar/Desmarcar) de todas as despesas do mês">✔</span>${m}`, 'th-mes');
  });
  h+=th('Total') + '</tr></thead><tbody>';
  const fixasCtx = window.CFDomainFixas.buildFixasContext(dados.fixas||[], cats);
  
  const totalFixasDaCategoriaDin = function(cat, mes) {
      const fixasDaCat = (dados.fixas || []).filter(f => f.cat_id === cat.id || (cat.inclui_fixas && !f.cat_id));
      const fixasAplicadasManual = dados.fixas_aplicadas_manual || {};
      let sum = 0;
      fixasDaCat.forEach(f => {
          const isExpiredAuto = mes && window.isFixaExpirada && window.isFixaExpirada(f, mes, ano);
          const isAplicadaManual = fixasAplicadasManual[`${f.id}_${mes}`];
          if (isExpiredAuto || isAplicadaManual) return;
          sum += f.valor;
      });
      return sum;
  };

  cats.forEach((cat,cidx)=>{
    const d=desp[cat.nome]||{}; let tot=0;
    const fixaFlag=cat.inclui_fixas?1:0;
    const cnSafe=cat.nome.replace(/'/g,"\\'");
    const fixasDaCatAll = (dados.fixas || []).filter(f => f.cat_id === cat.id || (cat.inclui_fixas && !f.cat_id));
    const totalFixasCatOriginal = fixasDaCatAll.reduce((s,f)=>s+f.valor, 0);
    const badge=totalFixasCatOriginal?`<span class="fixas-badge">&#9906; Fixas</span>`:'';
    const contaVinc=cat.conta_vinculada_id?(dados.contas||[]).find(c=>c.id==cat.conta_vinculada_id):null;
    const badgeConta=contaVinc?`<span class="fixas-badge badge-conta">&#10020; ${contaVinc.nome}</span>`:'';
    const nomeFormatado = window.formatBankIcons ? window.formatBankIcons(cat.nome) : cat.nome;
    const linksCat = `
      <a href="#" onclick="event.preventDefault(); abrirLote('despesa','${cnSafe}',${cat.id})">&#8862; Lançar todos os meses</a>
      <a href="#" onclick="event.preventDefault(); abrirRen(${cat.id},'${cnSafe}',${fixaFlag},${cat.conta_vinculada_id||null},'${(cat.tooltip||'').replace(/'/g,"\\'")}')">&#9998; Configurar</a>
      <a href="#" class="text-danger" onclick="event.preventDefault(); apagarLinhaCat('${cnSafe}')">&#10005; Remover lançamentos</a>
      <a href="#" class="text-danger" onclick="event.preventDefault(); excluirCategoriaMenu(${cat.id}, '${cnSafe}')">&#10005; Remover categoria</a>`;
    h+=`<tr draggable="true" data-cat-id="${cat.id}" class="cat-row" ondragstart="dragStart(event,${cat.id})" ondragover="dragOver(event)" ondragleave="dragLeave(event)" ondrop="dragDrop(event,${cat.id})"><td class="cat-nome" title=""><div class="cc"><span title="${cat.tooltip || cat.nome}">${nomeFormatado}</span>${badge}${badgeConta}${window.buildKebabMenuHtml(linksCat, true)}</div></td>`;
    for(let m=1;m<=12;m++){
      const vLanc=d[m]?d[m].valor:0;
      const vIgnorado=d[m]?(d[m].valor_ignorado||0):0;
      const notas=d[m]?d[m].notas:'';
      const lastMod=d[m]?d[m].last_modified:null;
      
      const vFixasAtivas = totalFixasDaCategoriaDin(cat, m);
      const vFixasExpiradas = totalFixasCatOriginal - vFixasAtivas;
      
      const excKey=cat.id+'_'+m;
      const fixaExcluida=(dados.fixas_excecoes||{})[excKey]||false;
      const vFixas=!fixaExcluida?vFixasAtivas:0;
      const vTotal=vLanc+vFixas;
      const vTotalDisplay=vTotal+vIgnorado;
      tot+=vTotal;
      
      const tit = cat.nome + ': ' + MESES[m-1];
      const tit_modal = cat.nome + ' - ' + MESES[m-1];
      const tit_onclick = tit_modal.replace(/'/g, "\\'");
      if(vTotalDisplay!==0||fixaFlag||notas||totalFixasCatOriginal>0){
        let txt = '';
        let nota_class = '';
        if (vTotalDisplay !== 0) {
            txt = BRL(vTotalDisplay);
            if (vIgnorado !== 0 || (notas && notas.includes('💳'))) txt = '&#9645; ' + txt;
        } else if (notas) {
            if (notas.includes('💳')) {
                txt = '&#9645;';
            } else {
                txt = notas.substring(0, 15) + (notas.length > 15 ? '...' : '');
            }
            nota_class = 'nota';
        }
      
      if (window.formatBankIcons) txt = window.formatBankIcons(txt);
        if(totalFixasCatOriginal&&!fixaExcluida){
          txt+=`<br><small class="txt-fixas-ativas">(${BRL(vFixasAtivas)} fixas)</small>`;
        }
        if(totalFixasCatOriginal&&fixaExcluida){
          txt+=`<br><small class="txt-fixas-removidas">fixas removidas
            <span onclick="event.stopPropagation();toggleFixaExcecao(${cat.id},${m},false)"
              title="Restaurar fixas neste mês" class="btn-restore-fixa">↩</span></small>`;
        }
        const stUI = buildCellStatusUI(cat.nome, m, dados);
        h+=`<td class="${stUI.pgClass} td-status-cell">
          <span class="vc vc-multiline ${vTotalDisplay<0?'neg':''} ${nota_class}" onclick="abrirDet(${m},'${cnSafe}','${tit_onclick}')" onmouseenter="carregarTooltipDet(this, ${m}, '${cnSafe}', '${lastMod||''}')" title="${tit}">${txt}</span>
          <i class="st-icon ${stUI.stClass}" onclick="event.stopPropagation();toggleStatus('${cnSafe}',${m})" title="${stUI.stTip}">${stUI.iconTxt}</i>
        </td>`;
      } else {
        h+=`<td><span class="vc vz" onclick="abrirDet(${m},'${cnSafe}','${tit_onclick}')" title="Clique para lançar">+</span></td>`;
      }
    }
    h+=`<td class="total-col ${tot<0?'neg':''}">${BRL(tot)}</td></tr>`;
  })
  const recLabel=(dados.config&&dados.config.receita_label)||'Receitas';
  const linksRec = `
    <a href="#" onclick="event.preventDefault(); abrirLote('receita')">&#8862; Lançar todos os meses</a>
    <a href="#" onclick="event.preventDefault(); renomearReceita()">&#9998; Renomear</a>
    <a href="#" class="text-danger" onclick="event.preventDefault(); apagarTodasReceitas()">&#10005; Remover lançamentos</a>`;
  h+=`<tr class="tr-rec"><td class="cat-nome" title=""><div class="cc"><span>${recLabel}</span>${window.buildKebabMenuHtml(linksRec, false)}</div></td>`;
  let totR=0;
  const recMod = dados.receitas_mod || {};
  for(let m=1;m<=12;m++){
    const v=rec[m]||0; totR+=v;
    const lastMod = recMod[m];
    
    let titRec = 'Receitas: ' + MESES[m-1];
    
    const stUI = buildCellStatusUI('__rec__', m, dados);

    if(v) {
      h+=`<td class="${stUI.pgClass} td-status-cell">
        <span class="vc pos vc-multiline" onclick="verRec(${m})" onmouseenter="carregarTooltipDet(this, ${m}, '__rec__', '${lastMod||''}')" title="${titRec}">${BRL(v)}</span>
        <i class="st-icon ${stUI.stClass}" onclick="event.stopPropagation();toggleStatus('__rec__',${m})" title="${stUI.stTip}">${stUI.iconTxt}</i>
      </td>`;
    } else {
      h+=`<td><span class="vc vz" onclick="verRec(${m})" title="Lançar receita">+</span></td>`;
    }
  }
  h+=`<td class="total-col pos">${BRL(totR)}</td></tr>`;
  h+='<tr class="tr-total-desp"><td class="cat-nome" title=""><div class="cc"><span>&#9660; Total Despesas</span></div></td>';
  let totG=0;
  for(let m=1;m<=12;m++){
    const s = window.CFAppTabela.totalDespesasMes(dados, cats, m, totalFixasDaCategoriaDin);
    totG+=s;
    h+=`<td class="td-num txt-total-desp">${s?BRL(s):''}</td>`;
  }
  h+=`<td class="total-col txt-total-desp">${BRL(totG)}</td></tr>`;
  
  h+='<tr class="tr-mov"><td class="cat-nome" title=""><div class="cc"><span>&#8644; Movimenta&ccedil;&atilde;o</span></div></td>';
  let totMov=0;
  for(let m=1;m<=12;m++){
    const mv=movimentacoes[m];
    const itens = mv ? (Array.isArray(mv.items) ? mv.items : (Array.isArray(mv) ? mv : [mv])) : [];
    const v=mv?(typeof mv.valor === 'number' ? mv.valor : itens.reduce((s,item)=>s+(item.valor||0),0)):0; totMov+=v;
    const tit=itens.length ? (`${itens.length} movimentação(ões) - ${MESES[m-1]}`) : MESES[m-1];
    if(v!==0){
      h+=`<td><span class="vc ${v<0?'neg':'pos'}" onclick="abrirMov(${m})" title="${tit}">${BRL(v)}</span></td>`;
    } else {
      h+=`<td><span class="vc vz" onclick="abrirMov(${m})" title="Lançar movimentação">+</span></td>`;
    }
  }
  h+=`<td class="total-col ${totMov<0?'neg':totMov>0?'pos':''}">${BRL(totMov)}</td></tr>`;

  h+='<tr class="tr-saldo"><td class="cat-nome" title=""><div class="cc"><span>&#931; Saldo</span></div></td>';
  let totS=0;
  for(let m=1;m<=12;m++){
    const r2=rec[m]||0;
    const s=window.CFAppTabela.saldoMes(dados, cats, rec, m, totalFixasDaCategoriaDin);
    const temValor = (r2 !== 0) || (s !== 0);
    totS+=s;
    h+=`<td class="td-num ${temValor?(s<0?'neg':'pos'):''}">${temValor?BRL(s):''}</td>`;
  }
  h+=`<td class="total-col ${totS<0?'neg':'pos'}">${BRL(totS)}</td></tr>`;
  
  const contas=dados.contas||[];
  const saldos=dados.saldos||{};
  const movimentos=dados.movimentos||{};
  contas.forEach(conta=>{
    const cid=String(conta.id);
    const saldoConta=saldos[cid]||{};
    const cnSafeC=(conta.nome||'').replace(/'/g,"\\'").replace(/"/g,"&quot;");
      const nomeFormatado = window.formatBankIcons ? window.formatBankIcons(conta.nome) : conta.nome;
    const linksConta = `
      <a href="#" onclick="event.preventDefault(); abrirEditConta(${conta.id},'${cnSafeC}',${conta.saldo_inicial||0})">&#9998; Editar</a>
      <a href="#" class="text-danger" onclick="event.preventDefault(); confirmarDelConta(${conta.id})">&#10005; Excluir</a>`;
    h+=`<tr class="tr-conta"><td class="cat-nome" title=""><div class="cc"><span title="${conta.nome}">&#10020; ${nomeFormatado}</span>${window.buildKebabMenuHtml(linksConta, false)}</div></td>`;
    for(let m=1;m<=12;m++){
      const saldoMes=saldoConta[m]!==undefined?saldoConta[m]:null;
      const cls=saldoMes===null?'':saldoMes<0?'neg':'pos';
      h+=`<td><span class="vc-conta ${cls}" onclick="abrirDep(${conta.id},'${cnSafeC}',${m})" title="Saldo acumulado — clique para lançar">${saldoMes!==null?BRL(saldoMes):'<span class=\"txt-muted\">+</span>'}</span></td>`;
    }
    const saldoDez=saldoConta[12]||0;
    h+=`<td class="total-col ${saldoDez<0?'neg':'pos'}">${BRL(saldoDez)}</td></tr>`;
  });
  if(contas.length>0){
    h+='<tr class="tr-total-contas"><td class="cat-nome" title=""><div class="cc"><span>&#10020; Total Contas</span></div></td>';
    for(let m=1;m<=12;m++){
      const soma=contas.reduce((s,c)=>s+((saldos[String(c.id)]||{})[m]||0),0);
      h+=`<td class="td-num ${soma<0?'neg':'pos'} txt-bold">${BRL(soma)}</td>`;
    }
    const somaTotal=contas.reduce((s,c)=>s+((saldos[String(c.id)]||{})[12]||0),0);
    h+=`<td class="total-col ${somaTotal<0?'neg':'pos'}">${BRL(somaTotal)}</td></tr>`;
  }
  h+='</tbody></table>';
  document.getElementById('tw').innerHTML=h;
  if(window.CF_AplicarResize) window.CF_AplicarResize();
  aplicarScrollDespesas();
}

window.formatarLinhasTooltip = function(linhas) {
  const linhasValidas = linhas.filter(r => (r.valor || 0) !== 0);
  if (linhasValidas.length === 0) return '';

  let maxStr = '';
  const formatados = linhasValidas.map(r => {
    const vStr = (r.valor || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    if (vStr.length > maxStr.length) maxStr = vStr;
    return { vStr, texto: r.texto || '' };
  });
  
  return formatados.map(r => {
    const missingChars = maxStr.length - r.vStr.length;
    let pad = '';
    if (missingChars > 0) {
      const prefix = maxStr.substring(0, missingChars);
      pad = prefix.split('').map(c => (c === '.' || c === ',') ? '\u2008' : '\u2007').join('');
    }
    const traco = r.texto ? ' - ' + r.texto : '';
    return `${pad}${r.vStr}${traco}`;
  }).join('\n');
};

window.carregarTooltipDet = function(el, mes, cat, lastMod) {
  const cacheKey = `${cat}_${mes}_${lastMod}`;
  return carregarTooltipCompleto(el, cacheKey, async function() {
    const url = cat === '__rec__' ? `/api/receitas/${ano}/${mes}?_=${Date.now()}` : `/api/despesas_detalhe/${ano}/${mes}/${encodeURIComponent(cat)}?_=${Date.now()}`;
    const r = await fetch(url, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });
    const rows = await r.json();
    const nomeTitulo = cat === '__rec__' ? 'Receitas' : cat;
    let novoTit = `${nomeTitulo}: ${MESES[mes-1]}`;
    
    if (rows && rows.length > 0) {
      let maxMod = null;
      let maxTime = 0;
      const linhasDados = rows.map(r => {
        // Força a leitura apenas de colunas reais do banco. Ignora variáveis dinâmicas de API.
        const dt = r.data_alteracao || r.created_at || r.data_criacao;
        if (dt) {
          const t = new Date(dt.replace(' ', 'T') + 'Z').getTime();
          if (t && t > maxTime) { maxTime = t; maxMod = dt; }
          else if (!maxTime && (!maxMod || dt > maxMod)) maxMod = dt; // fallback
        }

        let txt = cat === '__rec__' ? (r.descricao + (r.nota ? ` (${r.nota})` : '')) : r.nota;
        if (r.ignorar_total) txt = '&#9645; ' + (txt || 'Cartão');
        
        return { valor: r.valor || 0, texto: txt };
      });
      
      const linhas = window.formatarLinhasTooltip(linhasDados);
      
      if (linhas) novoTit += `\n${linhas}`;
      
      if (maxMod) {
        novoTit += `\n\nÚltima alteração: ${formatarDataHoraBR(maxMod)}`;
      }
    }
    return novoTit;
  }, 'Erro ao carregar tooltip');
};
