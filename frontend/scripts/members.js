document.addEventListener('DOMContentLoaded', () => {
  const membersOverlay = document.getElementById('members-overlay');
  const membersBtn = document.getElementById('members-btn');
  const closeBtn = document.getElementById('members-close-btn');
  const membersList = document.getElementById('members-list');
  const membersPagination = document.getElementById('members-pagination');
  const addSection = document.getElementById('add-member-section');
  const newEmailInput = document.getElementById('new-member-email');
  const newRoleSelect = document.getElementById('new-member-role');
  const addMemberBtn = document.getElementById('add-member-btn');

  let currentBoardId = null;
  let currentUserRole = null;
  let currentUserId = null;

  membersBtn.addEventListener('click', () => {
    // Всегда берём актуальные данные из глобального скоупа board.js
    if (!window.boardId) return;
    currentBoardId = window.boardId;
    currentUserRole = window.userRole || 'reader';
    currentUserId = window.currentUserId;
    
    // Показываем/скрываем секцию добавления в зависимости от роли
    addSection.style.display = currentUserRole === 'owner' ? 'block' : 'none';
    
    loadMembers();
    membersOverlay.style.display = 'flex';
  });

  closeBtn.addEventListener('click', () => {
    membersOverlay.style.display = 'none';
  });
  membersOverlay.addEventListener('click', (e) => {
    if (e.target === membersOverlay) membersOverlay.style.display = 'none';
  });

  async function loadMembers(cursor = null, direction = 'after') {
    try {
      const params = new URLSearchParams({ direction, limit: 10 });
      if (cursor) params.append('cursor', cursor);
      const res = await api.get(`/boards/${currentBoardId}/members/?${params}`);
      if (!res.ok) throw new Error('Failed to load members');
      const data = await res.json();
      const itemsWithNames = await Promise.all(data.items.map(async (m) => {
        const username = await getUsername(m.user_id);
        return { ...m, username };
      }));
      renderMembers(itemsWithNames);
      renderPagination(data);
      // На случай, если роль изменилась во время загрузки
      addSection.style.display = currentUserRole === 'owner' ? 'block' : 'none';
    } catch (err) {
      membersList.innerHTML = `<p class="error-message">${err.message}</p>`;
    }
  }

  function renderMembers(members) {
    membersList.innerHTML = '';
    if (!members || members.length === 0) {
      membersList.innerHTML = '<p style="color:var(--text-secondary);">No members.</p>';
      return;
    }

    const isOwner = currentUserRole === 'owner';

    members.forEach(member => {
      const item = document.createElement('div');
      item.className = 'member-item';
      const initialsText = member.username ? member.username.charAt(0).toUpperCase() : 'U';
      const roleDisabled = !isOwner || member.user_id === currentUserId;
      const canRemove = isOwner && member.user_id !== currentUserId;

      item.innerHTML = `
        <div class="member-info">
          <div class="member-avatar">
            <img class="avatar-img" style="display:none;" />
            <span class="avatar-initials">${initialsText}</span>
          </div>
          <span class="member-name">${escapeHtml(member.username)}</span>
        </div>
        <div class="flex-row" style="gap:0.3rem;">
          <select class="member-role-select" data-member-id="${member.id}" data-user-id="${member.user_id}" ${roleDisabled ? 'disabled' : ''}>
            <option value="reader" ${member.role === 'reader' ? 'selected' : ''}>Reader</option>
            <option value="writer" ${member.role === 'writer' ? 'selected' : ''}>Writer</option>
            <option value="owner" ${member.role === 'owner' ? 'selected' : ''}>Owner</option>
          </select>
          ${canRemove ? `
            <button class="btn btn-icon remove-member-btn" data-member-id="${member.id}">
              <svg class="icon" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          ` : ''}
        </div>
      `;

      // Загружаем аватарку
      const img = item.querySelector('.avatar-img');
      const initialsEl = item.querySelector('.avatar-initials');
      setAvatar(member.user_id, img, initialsEl);

      const select = item.querySelector('.member-role-select');
      if (select && !roleDisabled) {
        select.addEventListener('change', async () => {
          const newRole = select.value;
          try {
            const res = await api.patch(`/boards/${currentBoardId}/members/${member.id}`, { role: newRole });
            if (!res.ok) {
              const err = await res.json();
              throw new Error(err.detail || 'Failed to update role');
            }
            // Обновить глобальную роль, если меняли себе
            if (member.user_id === currentUserId) {
              currentUserRole = newRole;
              window.userRole = newRole;
              document.getElementById('role-badge').textContent = newRole;
              window.refreshBoard();
            }
            await loadMembers(); // перезагрузить список
          } catch (err) {
            alert(err.message);
          }
        });
      }

      const removeBtn = item.querySelector('.remove-member-btn');
      if (removeBtn) {
        removeBtn.addEventListener('click', async () => {
          if (!confirm('Remove this member?')) return;
          try {
            const res = await api.delete(`/boards/${currentBoardId}/members/${member.id}`);
            if (!res.ok) {
              const err = await res.json();
              throw new Error(err.detail || 'Failed to remove member');
            }
            await loadMembers();
          } catch (err) {
            alert(err.message);
          }
        });
      }

      membersList.appendChild(item);
    });
  }

  function renderPagination(data) {
    membersPagination.innerHTML = '';
    if (data.previous_cursor) {
      const prevBtn = document.createElement('button');
      prevBtn.className = 'btn btn-ghost';
      prevBtn.textContent = 'Previous';
      prevBtn.addEventListener('click', () => loadMembers(data.previous_cursor, 'before'));
      membersPagination.appendChild(prevBtn);
    }
    if (data.next_cursor) {
      const nextBtn = document.createElement('button');
      nextBtn.className = 'btn btn-ghost';
      nextBtn.textContent = 'Next';
      nextBtn.addEventListener('click', () => loadMembers(data.next_cursor, 'after'));
      membersPagination.appendChild(nextBtn);
    }
  }

  addMemberBtn.addEventListener('click', async () => {
    const email = newEmailInput.value.trim();
    if (!email) {
      alert('Enter user email');
      return;
    }
    try {
      const userRes = await api.get(`/auth/users/by-email?email=${encodeURIComponent(email)}`);
      if (!userRes.ok) {
        if (userRes.status === 404) throw new Error('User not found');
        const err = await userRes.json();
        throw new Error(err.detail || 'Failed to find user');
      }
      const user = await userRes.json();
      const role = newRoleSelect.value;
      const addRes = await api.post(`/boards/${currentBoardId}/members/`, {
        user_id: user.id,
        role: role
      });
      if (!addRes.ok) {
        const err = await addRes.json();
        throw new Error(err.detail || 'Failed to add member');
      }
      newEmailInput.value = '';
      await loadMembers();
    } catch (err) {
      alert(err.message);
    }
  });
});