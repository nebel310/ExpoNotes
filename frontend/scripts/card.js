(() => {
  const overlay = document.getElementById('card-detail-overlay');
  const closeBtn = document.getElementById('card-detail-close-btn');
  const titleInput = document.getElementById('edit-card-title');
  const descInput = document.getElementById('edit-card-desc');
  const prioritySelect = document.getElementById('edit-card-priority');
  const dueInput = document.getElementById('edit-card-due');
  const editBtn = document.getElementById('card-edit-btn');
  const saveBtn = document.getElementById('card-save-btn');
  const cancelEditBtn = document.getElementById('card-cancel-edit-btn');
  const commentsContainer = document.getElementById('comments-container');
  const newCommentText = document.getElementById('new-comment-text');
  const addCommentBtn = document.getElementById('add-comment-btn');
  const commentsPagination = document.getElementById('comments-pagination');

  // Вложения
  const attachmentInfo = document.getElementById('attachment-info');
  const attachmentName = document.getElementById('attachment-name');
  const attachmentDownload = document.getElementById('attachment-download');
  const attachmentEmpty = document.getElementById('attachment-empty');
  const attachmentInput = document.getElementById('attachment-input');
  const uploadBtn = document.getElementById('upload-attachment-btn');

  let currentCard = null;
  let currentBoardOwner = null;
  let isWriter = false;
  let editMode = false;
  let commentsData = { items: [], nextCursor: null, prevCursor: null };

  window.openCardDetail = async function(cardId, boardOwnerId, userRole) {
    currentBoardOwner = boardOwnerId;
    isWriter = userRole === 'writer' || userRole === 'owner';
    try {
      const res = await api.get(`/cards/${cardId}`);
      if (!res.ok) throw new Error('Card not found');
      currentCard = await res.json();
      populateFields();
      renderAttachment();
      await loadComments();
      overlay.style.display = 'flex';
    } catch (err) {
      alert(err.message);
    }
  };

  function populateFields() {
    if (!currentCard) return;
    titleInput.value = currentCard.title || '';
    descInput.value = currentCard.description || '';
    prioritySelect.value = currentCard.priority || 'low';
    if (currentCard.due_date) {
      dueInput.value = currentCard.due_date.slice(0, 16);
    } else {
      dueInput.value = '';
    }
    setEditMode(false);
  }

  function setEditMode(on) {
    editMode = on;
    const disabled = !on || !isWriter;
    titleInput.disabled = disabled;
    descInput.disabled = disabled;
    prioritySelect.disabled = disabled;
    dueInput.disabled = disabled;
    uploadBtn.style.display = on ? 'inline-flex' : 'none';
    editBtn.style.display = !on ? 'inline-flex' : 'none';
    saveBtn.style.display = on ? 'inline-flex' : 'none';
    cancelEditBtn.style.display = on ? 'inline-flex' : 'none';
  }

  function renderAttachment() {
    if (!currentCard) return;
    if (currentCard.file_id) {
      attachmentInfo.style.display = 'flex';
      attachmentEmpty.style.display = 'none';
      attachmentName.textContent = `Вложение ${currentCard.file_id}`;
      attachmentDownload.href = `${AppConfig.BASE_URL}/files/${currentCard.file_id}`;
      attachmentDownload.download = `file_${currentCard.file_id}`;
    } else {
      attachmentInfo.style.display = 'none';
      attachmentEmpty.style.display = 'block';
    }
  }

  editBtn.addEventListener('click', () => setEditMode(true));
  cancelEditBtn.addEventListener('click', () => {
    populateFields();
    setEditMode(false);
  });

  saveBtn.addEventListener('click', async () => {
    if (!currentCard) return;
    const payload = {
      title: titleInput.value.trim(),
      description: descInput.value.trim(),
      priority: prioritySelect.value,
      due_date: dueInput.value ? new Date(dueInput.value).toISOString() : null,
      version: currentCard.version
    };
    try {
      const res = await api.patch(`/cards/${currentCard.id}`, payload);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Update failed');
      }
      currentCard = await res.json();
      populateFields();
      renderAttachment();
      if (window.refreshBoard) window.refreshBoard();
    } catch (err) {
      alert(err.message);
    }
  });

  closeBtn.addEventListener('click', () => {
    overlay.style.display = 'none';
  });
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.style.display = 'none';
  });

  // Загрузка файла
  uploadBtn.addEventListener('click', () => {
    attachmentInput.click();
  });

  attachmentInput.addEventListener('change', async () => {
    const file = attachmentInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploadRes = await fetch(`${AppConfig.BASE_URL}/files/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${api.getAccessToken()}`
        },
        body: formData
      });
      if (!uploadRes.ok) {
        const err = await uploadRes.json();
        throw new Error(err.detail || 'Upload failed');
      }
      const fileData = await uploadRes.json(); // предполагаем, что ответ содержит { id: ... }
      const fileId = fileData.id;

      // Обновляем карточку
      const patchRes = await api.patch(`/cards/${currentCard.id}`, {
        file_id: fileId,
        version: currentCard.version
      });
      if (!patchRes.ok) {
        const err = await patchRes.json();
        throw new Error(err.detail || 'Failed to attach file');
      }
      currentCard = await patchRes.json();
      renderAttachment();
      if (window.refreshBoard) window.refreshBoard();
    } catch (err) {
      alert(err.message);
    }
    // очищаем поле
    attachmentInput.value = '';
  });

  // Комментарии
  async function loadComments(cursor = null, direction = 'after') {
    try {
      const params = new URLSearchParams({ direction, limit: 5 });
      if (cursor) params.append('cursor', cursor);
      const res = await api.get(`/cards/${currentCard.id}/comments/?${params}`);
      if (!res.ok) throw new Error('Failed to load comments');
      commentsData = await res.json();
      renderComments();
    } catch (err) {
      commentsContainer.innerHTML = `<p class="error-message">${err.message}</p>`;
    }
  }

  async function renderComments() {
    commentsContainer.innerHTML = '';
    if (commentsData.items.length === 0) {
      commentsContainer.innerHTML = '<p style="color:var(--text-secondary);">No comments yet.</p>';
      return;
    }

    const itemsWithNames = await Promise.all(commentsData.items.map(async (c) => {
      const username = await getUsername(c.author_id);
      return { ...c, username };
    }));

    itemsWithNames.forEach(comment => {
      const el = document.createElement('div');
      el.className = 'comment';
      const canModify = comment.author_id === window.currentUserId || currentBoardOwner === window.currentUserId;
      el.innerHTML = `
        <div class="comment-author">${escapeHtml(comment.username)}</div>
        <div class="comment-text">${escapeHtml(comment.text)}</div>
        <div class="comment-date">${formatDate(comment.created_at)}</div>
        ${canModify ? `
          <div class="comment-actions">
            <button class="btn btn-icon edit-comment-btn" data-id="${comment.id}" data-text="${escapeHtml(comment.text)}">
              <svg class="icon" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button class="btn btn-icon delete-comment-btn" data-id="${comment.id}">
              <svg class="icon" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14"/></svg>
            </button>
          </div>
        ` : ''}
      `;
      commentsContainer.appendChild(el);
    });

    document.querySelectorAll('.edit-comment-btn').forEach(btn => {
      btn.addEventListener('click', () => startEditComment(btn.dataset.id, btn.dataset.text));
    });
    document.querySelectorAll('.delete-comment-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteComment(btn.dataset.id));
    });

    commentsPagination.innerHTML = '';
    if (commentsData.prevCursor) {
      const prevBtn = document.createElement('button');
      prevBtn.className = 'btn btn-ghost';
      prevBtn.textContent = 'Previous';
      prevBtn.addEventListener('click', () => loadComments(commentsData.prevCursor, 'before'));
      commentsPagination.appendChild(prevBtn);
    }
    if (commentsData.nextCursor) {
      const nextBtn = document.createElement('button');
      nextBtn.className = 'btn btn-ghost';
      nextBtn.textContent = 'Next';
      nextBtn.addEventListener('click', () => loadComments(commentsData.nextCursor, 'after'));
      commentsPagination.appendChild(nextBtn);
    }
  }

  addCommentBtn.addEventListener('click', async () => {
    const text = newCommentText.value.trim();
    if (!text) return;
    try {
      const res = await api.post(`/cards/${currentCard.id}/comments/`, { text });
      if (!res.ok) throw new Error((await res.json()).detail);
      newCommentText.value = '';
      await loadComments();
    } catch (err) {
      alert(err.message);
    }
  });

  function startEditComment(commentId, currentText) {
    const commentDiv = document.querySelector(`.edit-comment-btn[data-id="${commentId}"]`)?.closest('.comment');
    if (!commentDiv) return;
    const textDiv = commentDiv.querySelector('.comment-text');
    const oldText = textDiv.textContent;
    textDiv.innerHTML = `<input class="input-field" id="edit-comment-input-${commentId}" value="${escapeHtml(oldText)}"/>`;
    const actionsDiv = commentDiv.querySelector('.comment-actions');
    actionsDiv.innerHTML = `
      <button class="btn btn-icon save-comment-edit-btn" data-id="${commentId}">
        <svg class="icon" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
      </button>
      <button class="btn btn-icon cancel-comment-edit-btn" data-id="${commentId}">
        <svg class="icon" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
      </button>
    `;

    document.querySelector(`.save-comment-edit-btn[data-id="${commentId}"]`)?.addEventListener('click', () => saveCommentEdit(commentId));
    document.querySelector(`.cancel-comment-edit-btn[data-id="${commentId}"]`)?.addEventListener('click', () => {
      textDiv.textContent = oldText;
      renderComments();
    });
  }

  async function saveCommentEdit(commentId) {
    const input = document.getElementById(`edit-comment-input-${commentId}`);
    if (!input) return;
    const newText = input.value.trim();
    if (!newText) return;
    try {
      const res = await api.patch(`/comments/${commentId}`, { text: newText });
      if (!res.ok) throw new Error((await res.json()).detail);
      await loadComments();
    } catch (err) {
      alert(err.message);
    }
  }

  async function deleteComment(commentId) {
    if (!confirm('Delete comment?')) return;
    try {
      const res = await api.delete(`/comments/${commentId}`);
      if (!res.ok) throw new Error((await res.json()).detail);
      await loadComments();
    } catch (err) {
      alert(err.message);
    }
  }

  window.refreshBoard = null; // будет установлено из board.js
})();