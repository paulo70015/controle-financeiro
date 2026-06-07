(function (global) {
  "use strict";

  function isFixaExpirada(fixa, mes_coluna, ano_coluna) {
    const hoje = new Date();
    const diaAtual = hoje.getDate();
    const mesAtual = hoje.getMonth() + 1;
    const anoAtual = hoje.getFullYear();
    
    // Obter dia de início do mês fiscal (padrão: 25)
    const diaInicio = (typeof _cfgDiaInicioMesFiscal !== 'undefined') ? _cfgDiaInicioMesFiscal : 25;
    
    // Calcular mês fiscal (competência do cartão)
    // Antes do fechamento: mês atual + 1
    // Depois do fechamento: mês atual + 2
    let mesFiscal = mesAtual + 1; // Sempre +1 antes do fechamento
    let anoFiscal = anoAtual;
    
    if (diaAtual >= diaInicio) {
      // Já fechou o cartão, próximo mês fiscal
      mesFiscal = mesAtual + 2;
    }
    
    // Ajustar ano se necessário
    if (mesFiscal > 12) {
      mesFiscal = mesFiscal - 12;
      anoFiscal = anoAtual + 1;
    }
    
    // Verificar se a coluna é de um ano/mês anterior ao fiscal atual
    if (ano_coluna < anoFiscal) return true;
    if (ano_coluna > anoFiscal) return false;
    if (mes_coluna < mesFiscal) return true;
    if (mes_coluna > mesFiscal) return false;
    
    // Estamos no mês fiscal atual
    // Verificar se o dia da fixa já passou no ciclo fiscal
    const diaFixa = parseInt(fixa.dia);
    if (isNaN(diaFixa) || diaFixa <= 0) return false;
    
    // Lógica: o ciclo fiscal vai do dia X do mês anterior até o dia X-1 do mês atual
    // Ex: dia 25 → ciclo vai de 25/03 a 24/04 (competência Maio)
    
    // Se estamos antes do dia de fechamento (ex: hoje é 23/04, fechamento dia 25)
    if (diaAtual < diaInicio) {
      // Ciclo atual: do dia X do mês passado até hoje
      // Fixas com dia >= diaInicio já aconteceram no mês passado (aplicadas)
      // Fixas com dia < diaInicio e dia <= diaAtual também já aconteceram (aplicadas)
      if (diaFixa >= diaInicio) return true; // Aconteceu no mês passado
      if (diaFixa <= diaAtual) return true; // Aconteceu neste mês até hoje (inclusive)
    } else {
      // Estamos no dia de fechamento ou depois (ex: hoje é 25/04 ou 26/04)
      // Ciclo atual: do dia X até hoje
      // Fixas com dia >= diaInicio e dia <= diaAtual já aconteceram
      if (diaFixa >= diaInicio && diaFixa <= diaAtual) return true;
    }
    
    return false;
  }

  function getDespesaLancada(dados, categoriaNome, mes) {
    return (dados.despesas && dados.despesas[categoriaNome] && dados.despesas[categoriaNome][mes] && dados.despesas[categoriaNome][mes].valor) || 0;
  }

  function totalDespesasMes(dados, categorias, mes, funcTotalFixas) {
    let soma = 0;
    categorias.forEach(function (c) {
      soma += getDespesaLancada(dados, c.nome, mes);
      let vFixas = funcTotalFixas ? funcTotalFixas(c, mes) : 0;
      if ((dados.fixas_excecoes || {})[c.id + '_' + mes]) vFixas = 0;
      soma += vFixas;
    });
    return soma;
  }

  function saldoMes(dados, categorias, receitas, mes, funcTotalFixas) {
    const receita = receitas[mes] || 0;
    const despesas = totalDespesasMes(dados, categorias, mes, funcTotalFixas);
    const movMes = dados.movimentacoes && dados.movimentacoes[mes] ? dados.movimentacoes[mes] : null;
    const mv = movMes
      ? (typeof movMes.valor === 'number'
        ? movMes.valor
        : ((movMes.items || []).reduce((s, item) => s + (item.valor || 0), 0)))
      : 0;
    return receita - despesas - mv; // Movimentaçoes subtraídas (saque vira positivo no saldo)
  }

  global.CFAppTabela = {
    totalDespesasMes: totalDespesasMes,
    saldoMes: saldoMes,
  };
  global.isFixaExpirada = isFixaExpirada;
})(window);
