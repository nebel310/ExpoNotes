document.addEventListener('DOMContentLoaded', async () => {
  if (!api.getAccessToken()) {
    window.location.href = 'index.html';
    return;
  }

  let originalData = {};
  const usernameInput = document.getElementById('edit-username');
  const emailInput = document.getElementById('edit-email');
  const bioInput = document.getElementById('edit-bio');
  const genderSelect = document.getElementById('edit-gender');
  const birthInput = document.getElementById('edit-birth');
  const avatarImg = document.getElementById('profile-avatar-img');
  const avatarInitials = document.getElementById('profile-avatar-initials');
  const profileUsername = document.getElementById('profile-username');
  const errorEl = document.getElementById('profile-error');
  const cancelBtn = document.getElementById('cancel-edit-btn');
  const avatarInput = document.getElementById('avatar-input');
  const changeAvatarBtn = document.getElementById('change-avatar-btn');

  try {
    const res = await api.get('/auth/me');
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to load profile');
    }
    const user = await res.json();
    originalData = user;
    populateForm(user);
    loadAvatar(user);
  } catch (err) {
    alert(err.message);
    window.location.href = 'boards.html';
  }

  function populateForm(user) {
    usernameInput.value = user.username || '';
    emailInput.value = user.email || '';
    bioInput.value = user.bio || '';
    genderSelect.value = user.gender || '';
    birthInput.value = user.birth_date ? user.birth_date.slice(0, 10) : '';
    profileUsername.textContent = user.username || 'Unknown';
  }

  async function loadAvatar(user) {
    if (user.avatar_id) {
      try {
        const token = api.getAccessToken();
        const response = await fetch(`${AppConfig.BASE_URL}/files/${user.avatar_id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          avatarImg.src = url;
          avatarImg.style.display = 'block';
          avatarInitials.style.display = 'none';
        } else {
          throw new Error('Failed to load avatar');
        }
      } catch (e) {
        avatarImg.style.display = 'none';
        avatarInitials.style.display = 'flex';
        avatarInitials.textContent = (user.username || 'U')[0].toUpperCase();
      }
    } else {
      avatarImg.style.display = 'none';
      avatarInitials.style.display = 'flex';
      avatarInitials.textContent = (user.username || 'U')[0].toUpperCase();
    }
  }

  cancelBtn.addEventListener('click', () => {
    populateForm(originalData);
    loadAvatar(originalData);
    errorEl.textContent = '';
  });

  document.getElementById('profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.textContent = '';

    const payload = {
      username: usernameInput.value.trim() || null,
      email: emailInput.value.trim() || null,
      bio: bioInput.value.trim() || null,
      gender: genderSelect.value || null,
      birth_date: birthInput.value ? new Date(birthInput.value).toISOString() : null,
    };
    Object.keys(payload).forEach(key => {
      if (payload[key] === null || payload[key] === '') delete payload[key];
    });

    try {
      const res = await api.patch('/auth/me', payload);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Update failed');
      }
      const updated = await res.json();
      originalData = updated;
      populateForm(updated);
      loadAvatar(updated);
      alert('Profile updated');
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });

  // Смена аватарки
  changeAvatarBtn.addEventListener('click', () => avatarInput.click());

  avatarInput.addEventListener('change', async () => {
    const file = avatarInput.files[0];
    if (!file) return;

    // Дополнительная проверка на клиенте (accept уже стоит, но на всякий случай)
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      alert('Only PNG and JPG images are allowed');
      avatarInput.value = '';
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploadRes = await fetch(`${AppConfig.BASE_URL}/files/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${api.getAccessToken()}` },
        body: formData
      });
      if (!uploadRes.ok) {
        const err = await uploadRes.json();
        throw new Error(err.detail || 'Upload failed');
      }
      const fileData = await uploadRes.json();
      const fileId = fileData.id;

      const patchRes = await api.patch('/auth/me', { avatar_id: fileId });
      if (!patchRes.ok) {
        const err = await patchRes.json();
        throw new Error(err.detail || 'Failed to update avatar');
      }
      const updatedUser = await patchRes.json();
      originalData = updatedUser;
      loadAvatar(updatedUser);
      // Очистить кэш аватарок для этого пользователя, чтобы везде обновилось
      if (avatarUrlCache[fileId]) delete avatarUrlCache[fileId];
      // Также сбросим кэш пользователя, чтобы setAvatar запросил новые данные
      if (userCache[updatedUser.id]) delete userCache[updatedUser.id];
    } catch (err) {
      alert(err.message);
    }
    avatarInput.value = '';
  });

  document.getElementById('logout-btn').addEventListener('click', async () => {
    try { await api.post('/auth/logout'); } catch (e) {}
    api.clearTokens();
    window.location.href = 'index.html';
  });

  document.getElementById('back-btn').addEventListener('click', () => {
    window.location.href = 'boards.html';
  });
});