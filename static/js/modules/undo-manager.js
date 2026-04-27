class UndoManager {
  constructor(btnId, deleteQueueRef) {
    this.stack = [];
    this.btnId = btnId;
    this.deleteQueueRef = deleteQueueRef;
  }
  
  push(action) {
    this.stack.push(action);
    this.showButton();
  }
  
  async undo(reloadFn, recarregarDetalhesFn) {
    if (!this.stack.length) return;
    const action = this.stack.pop();
    
    switch(action.type) {
      case 'delete':
        if (this.deleteQueueRef && Array.isArray(this.deleteQueueRef.queue)) {
          this.deleteQueueRef.queue = this.deleteQueueRef.queue.filter(item => {
            if (typeof item === 'object' && item.id !== undefined) {
              return item.id !== action.id;
            }
            return item !== action.id;
          });
        }
        break;
        
      case 'edit':
        await fetch(action.url, {
          method: 'PUT',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(action.oldBody)
        });
        if (reloadFn) await reloadFn();
        break;
        
      case 'toggle_fixas':
        await fetch('/api/fixa_excecao', {
          method: action.excluir ? 'POST' : 'DELETE',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ano: ano, mes: action.mes, cat_id: action.catId})
        });
        if (reloadFn) await reloadFn();
        break;
        
      case 'remove_projection':
        await fetch('/api/rendimento/lancamento/' + action.id, {method: 'DELETE'});
        if (reloadFn) await reloadFn();
        break;
        
      case 'reactivate_projection':
        await safeApiCall('/api/rendimento/lancamento', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            ano: action.ano, 
            mes: action.mes, 
            local_id: action.local_id, 
            tipo: 'rendimento', 
            valor: 0, 
            nota: 'Projeção cancelada' 
          })
        }, 'Falha ao desfazer reativação');
        if (reloadFn) await reloadFn();
        break;
    }
    
    if (recarregarDetalhesFn) await recarregarDetalhesFn();
    if (!this.stack.length) this.hideButton();
  }
  
  clear() {
    this.stack = [];
    this.hideButton();
  }
  
  showButton() {
    const btn = document.getElementById(this.btnId);
    if (btn) btn.style.display = 'inline-block';
  }
  
  hideButton() {
    const btn = document.getElementById(this.btnId);
    if (btn) btn.style.display = 'none';
  }
  
  get length() {
    return this.stack.length;
  }
}
