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
  if (userCache[userId]) return userCache[userId];
  try {
    const res = await api.get(`/auth/users/${userId}`);
    if (res.ok) {
      const user = await res.json();
      userCache[userId] = user.username;
      return user.username;
    }
  } catch (e) {}
  userCache[userId] = `User #${userId}`;
  return userCache[userId];
}