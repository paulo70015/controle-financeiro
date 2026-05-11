window.BANK_ICONS_CFG = {
  '[BB]': { label: 'BB', bg: '#F9D342', color: '#003DA5', title: 'Banco do Brasil' },
  '[CX]': { label: 'CX', bg: '#005CA9', color: '#F28E13', title: 'Caixa Econômica' },
  '[NU]': { label: 'NU', bg: '#8A05BE', color: '#FFF', title: 'Nubank' }
};

window.formatBankIcons = function(text) {
  if (typeof text !== 'string' || !text.includes('[')) return text;
  
  let newText = text;
  for (const [tag, b] of Object.entries(window.BANK_ICONS_CFG)) {
    const regex = new RegExp(tag.replace(/\[/g, '\\[').replace(/\]/g, '\\]'), 'gi');
    if (regex.test(newText)) {
      const badge = `<span style="display:inline-flex; align-items:center; justify-content:center; background:${b.bg}; color:${b.color}; font-size:10px; font-weight:900; width:22px; height:14px; border-radius:3px; vertical-align:middle; margin:0 3px; line-height:1; transform:translateY(-1px);" title="${b.title}">${b.label}</span>`;
      newText = newText.replace(regex, badge);
    }
  }
  return newText;
};

window.injectBankSelector = function(inputId) {
  const input = document.getElementById(inputId);
  if (!input || input.dataset.hasBankSelector) return;
  
  const container = document.createElement('div');
  container.className = 'bank-selector-container';
  container.style.cssText = 'display:flex; gap:6px; margin-top:4px; margin-bottom:8px;';
  
  for (const [tag, b] of Object.entries(window.BANK_ICONS_CFG)) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.innerHTML = b.label;
    btn.title = `Adicionar ícone ${b.label}`;
    btn.style.cssText = `background:${b.bg}; color:${b.color}; border:none; border-radius:4px; padding:2px 6px; font-size:11px; font-weight:bold; cursor:pointer; transition: opacity 0.2s;`;
    btn.onmouseover = () => btn.style.opacity = '0.8';
    btn.onmouseout = () => btn.style.opacity = '1';
    btn.onclick = (e) => {
      e.preventDefault();
      input.value = (input.value + ' ' + tag).trim();
      input.focus();
    };
    container.appendChild(btn);
  }
  
  input.parentNode.insertBefore(container, input.nextSibling);
  input.dataset.hasBankSelector = 'true';
};

function buildRowDetalheHtml(valStr, color, text, btnAction, btnEditAction = '') {
  const formattedText = window.formatBankIcons ? window.formatBankIcons(text) : text;
  return `<div class="di">
    <div class="di-texts">
      <span class="di-val" style="color:${color}">${valStr}</span>
      ${formattedText ? `<span class="di-desc">${formattedText}</span>` : ''}
    </div>
    ${btnEditAction ? `<button class="btn-edit" onclick="${btnEditAction}" title="Editar">&#9998;</button>` : ''}
    ${btnAction ? `<button class="btn-delete" onclick="${btnAction}" title="Excluir">&#10005;</button>` : ''}
  </div>`;
}

function fecharMenusKebab() {
  // Se temos um menu transportado para o body, nós o devolvemos para a tabela primeiro
  if (window._activeKebab) {
    const { menu, parent, nextSibling, btn } = window._activeKebab;
    menu.classList.remove('show');
    menu.style.position = '';
    menu.style.top = '';
    menu.style.left = '';
    menu.style.bottom = '';
    menu.style.zIndex = '';
    if (btn) btn.classList.remove('menu-open');
    
    if (parent && document.body.contains(parent)) parent.insertBefore(menu, nextSibling);
    else menu.remove();
    
    window._activeKebab = null;
  }

  document.querySelectorAll('.dropdown-content.show').forEach(el => {
    el.classList.remove('show');
    el.style.position = '';
    el.style.top = '';
    el.style.left = '';
    el.style.bottom = '';
  });
}

window.toggleCatMenu = function(e) {
  e.preventDefault();
  e.stopPropagation();
  const btn = e.currentTarget;
  
  // Se o botão clicado for o que já está aberto, apenas fechamos
  if (btn.classList.contains('menu-open')) {
    fecharMenusKebab();
    return;
  }
  
  fecharMenusKebab();
  
  const menu = btn.parentElement.querySelector('.dropdown-content');
  if (!menu) return;

  // Armazenamos a referência original antes de teleportá-lo para o body
  window._activeKebab = {
    menu: menu,
    parent: btn.parentElement,
    nextSibling: menu.nextSibling,
    btn: btn
  };
  
  // O pulo do gato: mover para o body quebra qualquer restrição de tabela ou rolagem
  document.body.appendChild(menu);
  btn.classList.add('menu-open');
  
  const rect = btn.getBoundingClientRect();
  menu.style.position = 'fixed';
  menu.style.zIndex = '999999';
    
  const spaceBelow = window.innerHeight - rect.bottom;
  if (spaceBelow < 150) {
    menu.style.top = 'auto';
    menu.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
  } else {
    menu.style.bottom = 'auto';
    menu.style.top = (rect.bottom + 4) + 'px';
  }
    
  let leftPos = rect.left;
  if (leftPos + 220 > window.innerWidth) leftPos = window.innerWidth - 230;
  menu.style.left = leftPos + 'px';
    
  menu.classList.add('show');
};

document.addEventListener('click', function(e) {
  if (!e.target.matches('.btn-kebab')) fecharMenusKebab();
});

window.addEventListener('scroll', function(e) {
  if (e.target.closest && e.target.closest('.dropdown-content')) return;
  fecharMenusKebab();
}, true);

// Utilitário DRY para gerar o Kebab Menu dinamicamente
window.buildKebabMenuHtml = function(linksHtml, dragHandle = false) {
  let h = `<div class="cat-actions-menu">
    <button class="eb btn-kebab" onclick="toggleCatMenu(event)" title="Opções">⋮</button>
    <div class="dropdown-content">${linksHtml}</div>
  </div>`;
  if (dragHandle) h += `<span class="drag-handle" title="Arrastar para reordenar">&#8801;</span>`;
  return `<div class="cc-actions">${h}</div>`;
};

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

const tooltipCache = new Map();

function limparCacheTooltip() {
  tooltipCache.clear();
}

window.iniciarEdicaoInline = function(config) {
  if (config.checkLock !== false && typeof isAnoBloqueado !== 'undefined' && isAnoBloqueado) {
    alert('Este ano está travado. Desbloqueie primeiro para editar.');
    return;
  }

  if (typeof config.onInit === 'function') {
    config.onInit();
  }

  if (Array.isArray(config.campos)) {
    config.campos.forEach(campo => {
      const el = document.getElementById(campo.id);
      if (el) {
        if (campo.type === 'checkbox') {
          el.checked = !!campo.valor;
        } else {
          const val = (campo.valor !== undefined && campo.valor !== null) ? campo.valor : '';
          el.value = typeof campo.formatar === 'function' ? campo.formatar(val) : val;
        }
      }
    });
  }

  if (typeof config.toggleFn === 'function') {
    config.toggleFn(true);
  }

  if (config.focusId) {
    if (typeof focarCampo === 'function') {
      focarCampo(config.focusId);
    } else {
      const focusEl = document.getElementById(config.focusId);
      if (focusEl) focusEl.focus();
    }
  }
};
