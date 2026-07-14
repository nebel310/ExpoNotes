document.addEventListener('DOMContentLoaded', async () => {
  if (!api.getAccessToken()) {
    window.location.href = 'index.html';
    return;
  }

  let currentUserId = null;
  let boards = [];
  let nextCursor = null;
  let prevCursor = null;
  const container = document.getElementById('boards-container');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const profileLink = document.getElementById('profile-link');

  // Получить текущего пользователя и обновить ссылку на профиль
  try {
    const res = await api.get('/auth/me');
    if (res.ok) {
      const user = await res.json();
      currentUserId = user.id;
      profileLink.textContent = user.username;
    }
  } catch (e) {
    console.warn('Could not fetch user', e);
  }

  // Загрузка досок
  async function loadBoards(cursor = null, direction = 'after') {
    try {
      const params = new URLSearchParams({ direction, limit: 10 });
      if (cursor) params.append('cursor', cursor);
      const response = await api.get(`/boards/?${params.toString()}`);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to load boards');
      }
      const data = await response.json();
      boards = data.items || [];
      nextCursor = data.next_cursor;
      prevCursor = data.previous_cursor;
      renderBoards();
      updatePaginationButtons();
    } catch (error) {
      alert(error.message);
    }
  }

  function renderBoards() {
    container.innerHTML = '';
    if (boards.length === 0) {
      container.innerHTML = '<p style="color: var(--text-secondary);">No boards yet. Create one!</p>';
      return;
    }
    boards.forEach(board => {
      const card = document.createElement('div');
      card.className = 'board-card';
      card.innerHTML = `
        <div class="board-card-title">${escapeHtml(board.title)}</div>
        <div class="board-card-desc">${escapeHtml(board.description || '')}</div>
        <div class="board-card-meta">Created ${formatDate(board.created_at)}</div>
        ${board.owner_id === currentUserId ? `
          <div class="board-card-actions">
            <button class="btn btn-icon delete-board-btn" data-id="${board.id}" aria-label="Delete board">
              <svg class="icon" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14"/></svg>
            </button>
          </div>
        ` : ''}
      `;
      card.addEventListener('click', (e) => {
        if (e.target.closest('.delete-board-btn')) return;
        window.location.href = `board.html?id=${board.id}`;
      });
      container.appendChild(card);
    });

    document.querySelectorAll('.delete-board-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const boardId = btn.dataset.id;
        if (confirm('Delete this board?')) {
          try {
            const res = await api.delete(`/boards/${boardId}`);
            if (!res.ok) {
              const err = await res.json();
              throw new Error(err.detail || 'Delete failed');
            }
            boards = boards.filter(b => b.id != boardId);
            renderBoards();
          } catch (error) {
            alert(error.message);
          }
        }
      });
    });
  }

  function updatePaginationButtons() {
    prevBtn.disabled = !prevCursor;
    nextBtn.disabled = !nextCursor;
  }

  prevBtn.addEventListener('click', () => {
    if (prevCursor) loadBoards(prevCursor, 'before');
  });

  nextBtn.addEventListener('click', () => {
    if (nextCursor) loadBoards(nextCursor, 'after');
  });

  const createModal = document.getElementById('create-modal');
  const createBoardBtn = document.getElementById('create-board-btn');
  const closeModalBtn = document.getElementById('close-modal-btn');
  const cancelCreateBtn = document.getElementById('cancel-create-btn');
  const createBtn = document.getElementById('create-btn');
  const newTitleInput = document.getElementById('new-board-title');
  const newDescInput = document.getElementById('new-board-desc');

  function openModal() { createModal.style.display = 'flex'; }
  function closeModal() { createModal.style.display = 'none'; newTitleInput.value = ''; newDescInput.value = ''; }

  createBoardBtn.addEventListener('click', openModal);
  closeModalBtn.addEventListener('click', closeModal);
  cancelCreateBtn.addEventListener('click', closeModal);
  createModal.addEventListener('click', (e) => { if (e.target === createModal) closeModal(); });

  createBtn.addEventListener('click', async () => {
    const title = newTitleInput.value.trim();
    if (!title) {
      alert('Title is required');
      return;
    }
    try {
      const res = await api.post('/boards/', { title, description: newDescInput.value.trim() || undefined });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Creation failed');
      }
      closeModal();
      await loadBoards();
    } catch (error) {
      alert(error.message);
    }
  });

  document.getElementById('logout-btn').addEventListener('click', async () => {
    try {
      await api.post('/auth/logout');
    } catch (e) {}
    api.clearTokens();
    window.location.href = 'index.html';
  });

  await loadBoards();
});