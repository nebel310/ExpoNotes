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
  const avatarDiv = document.getElementById('profile-avatar');
  const profileUsername = document.getElementById('profile-username');
  const errorEl = document.getElementById('profile-error');
  const cancelBtn = document.getElementById('cancel-edit-btn');

  try {
    const res = await api.get('/auth/me');
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to load profile');
    }
    const user = await res.json();
    originalData = user;
    populateForm(user);
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
    const initials = (user.username || 'U')[0].toUpperCase();
    avatarDiv.textContent = initials;
    profileUsername.textContent = user.username || 'Unknown';
  }

  cancelBtn.addEventListener('click', () => {
    populateForm(originalData);
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
      alert('Profile updated');
    } catch (err) {
      errorEl.textContent = err.message;
    }
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