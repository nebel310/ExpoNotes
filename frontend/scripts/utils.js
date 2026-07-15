// Общие утилиты
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Кэш пользователей
const userCache = {};

async function getUsername(userId) {
  if (!userId) return 'Unknown';
  if (userCache[userId]) return userCache[userId].username || `User #${userId}`;
  try {
    const res = await api.get(`/auth/users/${userId}`);
    if (res.ok) {
      const user = await res.json();
      userCache[userId] = user;
      return user.username;
    }
  } catch (e) {}
  userCache[userId] = { username: `User #${userId}` };
  return userCache[userId].username;
}

// Кэш URL аватарок
const avatarUrlCache = {};

async function setAvatar(userId, imgElement, initialsElement) {
  if (!userId) {
    if (imgElement) imgElement.style.display = 'none';
    if (initialsElement) initialsElement.style.display = 'flex';
    return;
  }

  try {
    // Получаем пользователя (если ещё нет в кэше)
    let user = userCache[userId];
    if (!user) {
      const res = await api.get(`/auth/users/${userId}`);
      if (res.ok) {
        user = await res.json();
        userCache[userId] = user;
      } else {
        throw new Error('User not found');
      }
    }

    if (user.avatar_id) {
      const avatarId = user.avatar_id;
      // Если уже есть URL в кэше
      if (avatarUrlCache[avatarId]) {
        imgElement.src = avatarUrlCache[avatarId];
        imgElement.style.display = 'block';
        if (initialsElement) initialsElement.style.display = 'none';
        return;
      }

      // Загружаем файл аватарки
      const token = api.getAccessToken();
      const response = await fetch(`${AppConfig.BASE_URL}/files/${avatarId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        avatarUrlCache[avatarId] = url;
        imgElement.src = url;
        imgElement.style.display = 'block';
        if (initialsElement) initialsElement.style.display = 'none';
      } else {
        throw new Error('Failed to load avatar');
      }
    } else {
      // Нет аватарки – показываем инициалы
      imgElement.style.display = 'none';
      if (initialsElement) initialsElement.style.display = 'flex';
    }
  } catch (e) {
    imgElement.style.display = 'none';
    if (initialsElement) initialsElement.style.display = 'flex';
  }
}