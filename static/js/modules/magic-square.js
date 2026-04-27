// --- QUADRADO MÁGICO (Seleção e Soma Dinâmica) ---
document.addEventListener('DOMContentLoaded', () => {
  const magicBox = document.createElement('div');
  magicBox.id = 'magic-box';
  document.body.appendChild(magicBox);

  const magicTotal = document.createElement('div');
  magicTotal.id = 'magic-total';
  document.body.appendChild(magicTotal);

  let isSelecting = false;
  let startX = 0, startY = 0;
  let hideTimeout = null;

  document.addEventListener('mousedown', e => {
    if (!e.shiftKey) return; // Só ativa se segurar SHIFT
    if (e.target.closest('input, textarea, button, select')) return; // Ignora campos de formulário

    isSelecting = true;
    startX = e.clientX;
    startY = e.clientY;
    magicBox.style.display = 'block';
    magicBox.style.left = startX + 'px';
    magicBox.style.top = startY + 'px';
    magicBox.style.width = '0px';
    magicBox.style.height = '0px';
    
    magicTotal.style.display = 'none';
    magicTotal.style.opacity = '1';
    clearTimeout(hideTimeout);
    
    e.preventDefault(); // Evita selecionar o texto nativo da página
  });

  document.addEventListener('mousemove', e => {
    if (!isSelecting) return;
    
    const currentX = e.clientX;
    const currentY = e.clientY;
    const left = Math.min(startX, currentX);
    const top = Math.min(startY, currentY);
    const width = Math.abs(currentX - startX);
    const height = Math.abs(currentY - startY);
    
    magicBox.style.left = left + 'px';
    magicBox.style.top = top + 'px';
    magicBox.style.width = width + 'px';
    magicBox.style.height = height + 'px';

    calcularSomaMagic(left, top, width, height);
  });

  document.addEventListener('mouseup', () => {
    if (!isSelecting) return;
    isSelecting = false;
    magicBox.style.display = 'none';
    document.querySelectorAll('.magic-highlight').forEach(el => el.classList.remove('magic-highlight'));
    
    hideTimeout = setTimeout(() => {
      magicTotal.style.opacity = '0';
      setTimeout(() => magicTotal.style.display = 'none', 300);
    }, 3500);
  });

  function calcularSomaMagic(left, top, width, height) {
    const boxRect = { left, top, right: left + width, bottom: top + height };
    let soma = 0, count = 0;
    let root = document.querySelector('.ov.show') || document.querySelector('.drawer-panel.open') || document;

    root.querySelectorAll('.vc, .vc-conta, .td-num, .di-val, .mv, .rend-cell').forEach(el => {
      const rect = el.getBoundingClientRect();
      const overlap = !(boxRect.right < rect.left || boxRect.left > rect.right || boxRect.bottom < rect.top || boxRect.top > rect.bottom);
      if (overlap) { 
        el.classList.add('magic-highlight'); 
        let val = parseVal(el.textContent.split('\n')[0] || el.textContent); 
        if (val !== null) { 
          // Verifica se o número está sinalizado como negativo visualmente na UI
          const styleAttr = el.getAttribute('style') || '';
          const isNegativo = el.classList.contains('neg') || styleAttr.includes('#e53935') || styleAttr.includes('#c62828') || styleAttr.includes('var(--vermelho)');
          
          if (isNegativo && val > 0) val = -val;
          
          soma += val; 
          count++; 
        } 
      } 
      else { el.classList.remove('magic-highlight'); }
    });
    if (count > 0) { 
      const corSoma = soma < 0 ? 'color:var(--vermelho);' : '';
      magicTotal.style.display = 'block'; magicTotal.innerHTML = `Soma (${count} itens): <br><span style="font-size:24px;${corSoma}">${BRL(soma)}</span>`; 
    } 
    else { magicTotal.style.display = 'none'; }
  }
});