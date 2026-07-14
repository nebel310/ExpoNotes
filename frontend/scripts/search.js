document.addEventListener('DOMContentLoaded', () => {
  if (!api.getAccessToken()) {
    window.location.href = 'index.html';
    return;
  }

  const searchInput = document.getElementById('search-input');
  const searchBtn = document.getElementById('search-btn');
  const resultsContainer = document.getElementById('results-container');
  const pagination = document.getElementById('pagination');

  let currentQuery = '';
  let nextCursor = null;
  let prevCursor = null;

  async function performSearch(query, cursor = null, direction = 'after') {
    if (!query.trim()) return;
    currentQuery = query;
    try {
      const params = new URLSearchParams({ q: query, direction, limit: 10 });
      if (cursor) params.append('cursor', cursor);
      const res = await api.get(`/search/cards?${params}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Search failed');
      }
      const data = await res.json();
      nextCursor = data.next_cursor;
      prevCursor = data.previous_cursor;
      renderResults(data.items);
      renderPagination();
    } catch (err) {
      resultsContainer.innerHTML = `<p class="error-message">${err.message}</p>`;
    }
  }

  function renderResults(cards) {
    resultsContainer.innerHTML = '';
    if (!cards || cards.length === 0) {
      resultsContainer.innerHTML = '<p style="color: var(--text-secondary);">No cards found.</p>';
      return;
    }

    cards.forEach(card => {
      const item = document.createElement('div');
      item.className = 'card-result';
      const boardId = card.board_id; // теперь приходит в ответе
      item.innerHTML = `
        <div class="card-info">
          <div class="card-result-title">${escapeHtml(card.title)}</div>
          <div class="card-result-meta">
            Priority: ${card.priority || 'none'} · Column ID: ${card.column_id}
          </div>
        </div>
        ${boardId ? `<a class="card-result-link" href="board.html?id=${boardId}">Open board</a>` : '<span class="card-result-link" style="color:var(--text-secondary);">No board</span>'}
      `;
      if (boardId) {
        item.addEventListener('click', () => {
          window.location.href = `board.html?id=${boardId}`;
        });
      }
      resultsContainer.appendChild(item);
    });
  }

  function renderPagination() {
    pagination.innerHTML = '';
    if (prevCursor) {
      const prevBtn = document.createElement('button');
      prevBtn.className = 'btn btn-ghost';
      prevBtn.textContent = 'Previous';
      prevBtn.addEventListener('click', () => performSearch(currentQuery, prevCursor, 'before'));
      pagination.appendChild(prevBtn);
    }
    if (nextCursor) {
      const nextBtn = document.createElement('button');
      nextBtn.className = 'btn btn-ghost';
      nextBtn.textContent = 'Next';
      nextBtn.addEventListener('click', () => performSearch(currentQuery, nextCursor, 'after'));
      pagination.appendChild(nextBtn);
    }
  }

  searchBtn.addEventListener('click', () => {
    const q = searchInput.value.trim();
    if (!q) return;
    performSearch(q);
  });
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      searchBtn.click();
    }
  });

  // Навигация
  document.getElementById('back-btn').addEventListener('click', () => {
    window.location.href = 'boards.html';
  });
  document.getElementById('logout-btn').addEventListener('click', async () => {
    try { await api.post('/auth/logout'); } catch (e) {}
    api.clearTokens();
    window.location.href = 'index.html';
  });
});