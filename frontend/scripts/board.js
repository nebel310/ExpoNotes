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
  const profileLink = document.getElementById('profile-link');

  // Поиск
  const searchInput = document.getElementById('search-input');
  const searchBtn = document.getElementById('search-btn');
  const searchResults = document.getElementById('search-results');

  // WebSocket
  let ws = null;

  // Сохраним глобально
  window.boardId = boardId;
  window.currentBoardOwner = null;
  window.refreshBoard = null;

  async function init() {
    try {
      const userRes = await api.get('/auth/me');
      if (userRes.ok) {
        const user = await userRes.json();
        currentUserId = user.id;
        window.currentUserId = user.id;
        profileLink.textContent = user.username;
      }
      window.userRole = userRole;
      await loadBoardData();
      // Подключаем WebSocket после загрузки доски
      connectWebSocket();
    } catch (e) {
      alert('Failed to initialize board');
      window.location.href = 'boards.html';
    }
  }

  // ========== WebSocket ==========
  function connectWebSocket() {
    const token = api.getAccessToken();
    if (!token) return;

    // Закрываем предыдущее соединение, если было
    if (ws) {
      ws.close();
    }

    ws = new WebSocket(`${AppConfig.BASE_URL.replace('http', 'ws')}/ws?token=${encodeURIComponent(token)}`);

    ws.onopen = () => {
      // Подписываемся на доску
      ws.send(JSON.stringify({ type: 'subscribe', board_id: parseInt(boardId) }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'card_moved') {
          // Обновляем доску полностью
          loadBoardData();
        } else if (msg.type === 'subscribed') {
          console.log('WebSocket подписан на доску', msg.board_id);
        } else if (msg.type === 'error') {
          console.warn('WebSocket error:', msg.detail);
        }
      } catch (e) {}
    };

    ws.onclose = () => {
      // Попытка переподключения через 5 секунд, если страница не закрыта
      setTimeout(() => {
        if (document.visibilityState === 'visible') {
          connectWebSocket();
        }
      }, 5000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  }

  // При уходе со страницы закрываем соединение
  window.addEventListener('beforeunload', () => {
    if (ws) {
      ws.close();
    }
  });

  // ================================

  async function loadBoardData() {
    try {
      const boardRes = await api.get(`/boards/${boardId}`);
      if (!boardRes.ok) throw new Error('Board not found');
      const board = await boardRes.json();
      boardTitleEl.textContent = board.title;
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
        if (member) {
          userRole = member.role;
          window.userRole = userRole;
        }
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
            <div class="card ${card.priority ? 'priority-' + card.priority : ''}" draggable="${isWriter}" data-card-id="${card.id}">
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

    if (isWriter) {
      const addColBtn = document.createElement('button');
      addColBtn.className = 'btn';
      addColBtn.style.marginTop = '0.5rem';
      addColBtn.textContent = '+ Add Column';
      addColBtn.addEventListener('click', () => showModal('column'));
      boardContainer.appendChild(addColBtn);
    }

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

    document.querySelectorAll('[data-add-card]').forEach(btn => {
      btn.addEventListener('click', () => {
        const colId = btn.dataset.addCard;
        showModal('card', colId);
      });
    });

    document.querySelectorAll('.card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.card-delete')) return;
        const cardId = card.dataset.cardId;
        if (window.currentBoardOwner && window.openCardDetail) {
          window.openCardDetail(cardId, window.currentBoardOwner, userRole);
        }
      });
    });

    if (isWriter) {
      initDragAndDrop();
    }
  }

  // Drag & Drop
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
    const targetColumn = this;
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
      // WebSocket уже отправит уведомление всем, включая нас, но мы обновим доску сразу
      await loadBoardData();
    } catch (err) {
      alert(err.message);
      await loadBoardData();
    }
  }

  // Поиск
  async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
      searchResults.style.display = 'none';
      return;
    }
    try {
      const res = await api.get(`/search/cards?q=${encodeURIComponent(query)}&limit=5`);
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();
      showSearchResults(data.items);
    } catch (err) {
      searchResults.innerHTML = `<div class="search-result-item"><span class="search-result-title" style="color:#ff5c5c;">${err.message}</span></div>`;
      searchResults.style.display = 'block';
    }
  }

  function showSearchResults(cards) {
    searchResults.innerHTML = '';
    if (!cards.length) {
      searchResults.innerHTML = '<div class="search-result-item"><span class="search-result-title" style="color:var(--text-secondary);">No results</span></div>';
      searchResults.style.display = 'block';
      return;
    }
    cards.forEach(card => {
      const div = document.createElement('div');
      div.className = 'search-result-item';
      div.innerHTML = `
        <span class="search-result-title">${escapeHtml(card.title)}</span>
        <span class="search-result-board">Board #${card.board_id}</span>
      `;
      div.addEventListener('click', () => {
        searchResults.style.display = 'none';
        searchInput.value = '';
        if (card.board_id == boardId) {
          if (window.currentBoardOwner && window.openCardDetail) {
            window.openCardDetail(card.id, window.currentBoardOwner, userRole);
          }
        } else {
          if (confirm('This card is in another board. Open it?')) {
            window.location.href = `board.html?id=${card.board_id}`;
          }
        }
      });
      searchResults.appendChild(div);
    });
    searchResults.style.display = 'block';
  }

  searchBtn.addEventListener('click', performSearch);
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
      searchResults.style.display = 'none';
    }
  });

  // Модалка
  const modalOverlay = document.getElementById('modal-overlay');
  const modalTitle = document.getElementById('modal-title');
  const modalInput = document.getElementById('modal-input');
  const modalActionBtn = document.getElementById('modal-action-btn');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalCancelBtn = document.getElementById('modal-cancel-btn');
  let modalContext = { type: '', columnId: null };

  function showModal(type, columnId = null) {
    modalContext = { type, columnId };
    modalTitle.textContent = type === 'column' ? 'New Column' : 'New Card';
    modalInput.placeholder = type === 'column' ? 'Column name' : 'Card title';
    modalInput.value = '';
    modalOverlay.style.display = 'flex';
    modalInput.focus();
  }
  function hideModal() { modalOverlay.style.display = 'none'; }
  modalCloseBtn.addEventListener('click', hideModal);
  modalCancelBtn.addEventListener('click', hideModal);
  modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) hideModal(); });

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

  document.getElementById('back-btn').addEventListener('click', () => {
    window.location.href = 'boards.html';
  });
  document.getElementById('logout-btn').addEventListener('click', async () => {
    try { await api.post('/auth/logout'); } catch (e) {}
    api.clearTokens();
    window.location.href = 'index.html';
  });

  window.refreshBoard = () => loadBoardData();
  await init();
});