(function (global) {
  "use strict";

  function buildFixasContext(fixas, categorias) {
    const listaFixas = Array.isArray(fixas) ? fixas : [];
    const fixasPorCategoria = {};
    let totalFixas = 0;
    let totalFixasOrfas = 0;

    listaFixas.forEach(function (f) {
      const valor = Number(f.valor) || 0;
      totalFixas += valor;
      if (f.cat_id) {
        const key = String(f.cat_id);
        fixasPorCategoria[key] = (fixasPorCategoria[key] || 0) + valor;
      } else {
        totalFixasOrfas += valor;
      }
    });

    function totalFixasDaCategoria(cat) {
      const vinculadas = fixasPorCategoria[String(cat.id)] || 0;
      const orfas = cat.inclui_fixas ? totalFixasOrfas : 0;
      return vinculadas + orfas;
    }

    return {
      totalFixas: totalFixas,
      totalFixasOrfas: totalFixasOrfas,
      fixasPorCategoria: fixasPorCategoria,
      totalFixasDaCategoria: totalFixasDaCategoria,
    };
  }

  global.CFDomainFixas = {
    buildFixasContext: buildFixasContext,
  };
})(window);

