document.addEventListener('DOMContentLoaded', async () => {
  if (!api.getAccessToken()) {
    window.location.href = 'index.html';
    return;
  }

  const urlParams = new URLSearchParams(window.location.search);
  const boardId = urlParams.get('id');
  if (!boardId) {
    window.location.href = 'boards.html';
    return;
  }

  let currentUserId = null;
  let userRole = 'reader';
  let columns = [];
  const boardContainer = document.getElementById('board-container');
  const boardTitleEl = document.getElementById('board-title');
  const roleBadge = document.getElementById('role-badge');

  // Модальное окно (колонка/карточка)
  const modalOverlay = document.getElementById('modal-overlay');
  const modalTitle = document.getElementById('modal-title');
  const modalInput = document.getElementById('modal-input');
  const modalActionBtn = document.getElementById('modal-action-btn');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalCancelBtn = document.getElementById('modal-cancel-btn');
  let modalContext = { type: '', columnId: null };

  function showModal(type, columnId = null) {
    modalContext = { type, columnId };
    if (type === 'column') {
      modalTitle.textContent = 'New Column';
      modalInput.placeholder = 'Column name';
    } else {
      modalTitle.textContent = 'New Card';
      modalInput.placeholder = 'Card title';
    }
    modalInput.value = '';
    modalOverlay.style.display = 'flex';
    modalInput.focus();
  }

  function hideModal() {
    modalOverlay.style.display = 'none';
  }

  modalCloseBtn.addEventListener('click', hideModal);
  modalCancelBtn.addEventListener('click', hideModal);
  modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) hideModal();
  });

  modalActionBtn.addEventListener('click', async () => {
    const title = modalInput.value.trim();
    if (!title) return;

    try {
      if (modalContext.type === 'column') {
        const order = columns.length;
        const res = await api.post(`/boards/${boardId}/columns/`, { title, order });
        if (!res.ok) throw new Error((await res.json()).detail);
      } else if (modalContext.type === 'card' && modalContext.columnId) {
        const column = columns.find(c => c.id == modalContext.columnId);
        const cards = column?.cards || [];
        const order = cards.length;
        const res = await api.post(`/columns/${modalContext.columnId}/cards/`, { title, order });
        if (!res.ok) throw new Error((await res.json()).detail);
      }
      hideModal();
      await loadBoardData();
    } catch (err) {
      alert(err.message);
    }
  });

  // Инициализация
  async function init() {
    try {
      const userRes = await api.get('/auth/me');
      if (userRes.ok) {
        const user = await userRes.json();
        currentUserId = user.id;
        window.currentUserId = user.id;          // <-- глобально для card.js
      }
      await loadBoardData();
    } catch (e) {
      alert('Failed to initialize board');
      window.location.href = 'boards.html';
    }
  }

  async function loadBoardData() {
    try {
      const boardRes = await api.get(`/boards/${boardId}`);
      if (!boardRes.ok) throw new Error('Board not found');
      const board = await boardRes.json();
      boardTitleEl.textContent = board.title;

      // Сохраняем владельца доски глобально
      window.currentBoardOwner = board.owner_id;

      await loadUserRole();

      columns = await fetchAllColumns();
      for (const col of columns) {
        col.cards = await fetchAllCards(col.id);
      }

      renderBoard();
    } catch (err) {
      alert(err.message);
    }
  }

  async function loadUserRole() {
    try {
      const membersRes = await api.get(`/boards/${boardId}/members/?limit=50`);
      if (membersRes.ok) {
        const data = await membersRes.json();
        const member = data.items?.find(m => m.user_id === currentUserId);
        if (member) userRole = member.role;
      }
    } catch (e) {}
    roleBadge.textContent = userRole;
    roleBadge.style.display = 'inline-block';
  }

  async function fetchAllColumns() {
    let all = [];
    let cursor = null;
    while (true) {
      const params = new URLSearchParams({ direction: 'after', limit: 20 });
      if (cursor) params.append('cursor', cursor);
      const res = await api.get(`/boards/${boardId}/columns/?${params}`);
      if (!res.ok) break;
      const data = await res.json();
      all = all.concat(data.items);
      if (data.next_cursor) cursor = data.next_cursor;
      else break;
    }
    all.sort((a, b) => a.order - b.order);
    return all;
  }

  async function fetchAllCards(columnId) {
    let all = [];
    let cursor = null;
    while (true) {
      const params = new URLSearchParams({ direction: 'after', limit: 20 });
      if (cursor) params.append('cursor', cursor);
      const res = await api.get(`/columns/${columnId}/cards/?${params}`);
      if (!res.ok) break;
      const data = await res.json();
      all = all.concat(data.items);
      if (data.next_cursor) cursor = data.next_cursor;
      else break;
    }
    all.sort((a, b) => a.order - b.order);
    return all;
  }

  function renderBoard() {
    boardContainer.innerHTML = '';
    const isWriter = userRole === 'writer' || userRole === 'owner';

    columns.forEach(column => {
      const columnEl = document.createElement('div');
      columnEl.className = 'column';
      columnEl.dataset.columnId = column.id;
      columnEl.innerHTML = `
        <div class="column-header">
          <span class="column-title">${escapeHtml(column.title)}</span>
          ${isWriter ? `<button class="btn btn-icon column-delete-btn" data-delete-column="${column.id}">
            <svg class="icon" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14"/></svg>
          </button>` : ''}
        </div>
        <div class="column-cards" data-column-id="${column.id}">
          ${column.cards.map(card => `
            <div class="card" draggable="${isWriter}" data-card-id="${card.id}">
              <div class="card-title">${escapeHtml(card.title)}</div>
              ${isWriter ? `<button class="btn btn-icon card-delete" data-delete-card="${card.id}">
                <svg class="icon" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>` : ''}
            </div>
          `).join('')}
        </div>
        ${isWriter ? `<div class="column-footer">
          <button class="btn add-card-btn" data-add-card="${column.id}">Add Card</button>
        </div>` : ''}
      `;
      boardContainer.appendChild(columnEl);
    });

    // Кнопка добавления колонки
    if (isWriter) {
      const addColBtn = document.createElement('button');
      addColBtn.className = 'btn';
      addColBtn.style.marginTop = '0.5rem';
      addColBtn.textContent = '+ Add Column';
      addColBtn.addEventListener('click', () => showModal('column'));
      boardContainer.appendChild(addColBtn);
    }

    // Обработчики удаления колонок
    document.querySelectorAll('[data-delete-column]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm('Delete column and all cards?')) return;
        const colId = btn.dataset.deleteColumn;
        try {
          const res = await api.delete(`/columns/${colId}`);
          if (!res.ok) throw new Error((await res.json()).detail);
          await loadBoardData();
        } catch (err) { alert(err.message); }
      });
    });

    // Обработчики удаления карточек
    document.querySelectorAll('[data-delete-card]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm('Delete card?')) return;
        const cardId = btn.dataset.deleteCard;
        try {
          const res = await api.delete(`/cards/${cardId}`);
          if (!res.ok) throw new Error((await res.json()).detail);
          await loadBoardData();
        } catch (err) { alert(err.message); }
      });
    });

    // Кнопки добавления карточек
    document.querySelectorAll('[data-add-card]').forEach(btn => {
      btn.addEventListener('click', () => {
        const colId = btn.dataset.addCard;
        showModal('card', colId);
      });
    });

    // Обработчик клика на карточку – открытие детального просмотра
    document.querySelectorAll('.card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.card-delete')) return; // не открывать при клике на удаление
        const cardId = card.dataset.cardId;
        if (window.currentBoardOwner && window.openCardDetail) {
          window.openCardDetail(cardId, window.currentBoardOwner, userRole);
        }
      });
    });

    // Drag-and-drop
    if (isWriter) {
      initDragAndDrop();
    }
  }

  // ========== Drag & Drop ==========
  function initDragAndDrop() {
    const cards = document.querySelectorAll('.card');
    const columns = document.querySelectorAll('.column');

    cards.forEach(card => {
      card.addEventListener('dragstart', handleDragStart);
      card.addEventListener('dragend', handleDragEnd);
    });

    columns.forEach(column => {
      column.addEventListener('dragover', handleDragOver);
      column.addEventListener('dragleave', handleDragLeave);
      column.addEventListener('drop', handleDrop);
    });
  }

  let draggedCard = null;

  function handleDragStart(e) {
    draggedCard = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', '');
  }

  function handleDragEnd(e) {
    this.classList.remove('dragging');
    draggedCard = null;
    document.querySelectorAll('.column').forEach(col => col.classList.remove('drag-over'));
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    this.classList.add('drag-over');
  }

  function handleDragLeave(e) {
    this.classList.remove('drag-over');
  }

  async function handleDrop(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
    if (!draggedCard) return;

    const targetColumn = this; // .column
    const targetColumnId = targetColumn.dataset.columnId;
    const cardId = draggedCard.dataset.cardId;
    if (!targetColumnId || !cardId) return;

    const cardsContainer = targetColumn.querySelector('.column-cards');
    const dropTarget = e.target.closest('.card');
    let newOrder = 0;

    if (dropTarget && dropTarget !== draggedCard) {
      const allCards = [...cardsContainer.querySelectorAll('.card')];
      newOrder = allCards.indexOf(dropTarget);
      cardsContainer.insertBefore(draggedCard, dropTarget);
    } else {
      cardsContainer.appendChild(draggedCard);
      const allCards = [...cardsContainer.querySelectorAll('.card')];
      newOrder = allCards.length - 1;
    }

    try {
      const res = await api.post(`/cards/${cardId}/move`, {
        column_id: parseInt(targetColumnId),
        order: newOrder
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Move failed');
      }
      await loadBoardData();
    } catch (err) {
      alert(err.message);
      await loadBoardData();
    }
  }

  // Навигация
  document.getElementById('back-btn').addEventListener('click', () => {
    window.location.href = 'boards.html';
  });
  document.getElementById('logout-btn').addEventListener('click', async () => {
    try { await api.post('/auth/logout'); } catch (e) {}
    api.clearTokens();
    window.location.href = 'index.html';
  });

  // Функция обновления доски, доступная извне (для card.js)
  window.refreshBoard = () => loadBoardData();

  await init();
});