document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const switchButtons = document.querySelectorAll('.switch-btn');

  // Переключение форм
  switchButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetFormId = btn.dataset.switch;
      document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
      document.getElementById(targetFormId).classList.add('active');
      // Очистить ошибки
      document.querySelectorAll('.error-message').forEach(el => el.textContent = '');
    });
  });

  // Если уже залогинены — перенаправим на доски (позже)
  if (api.getAccessToken()) {
    // Можно сразу уйти на boards.html, но пока нет файла, оставим как есть
    // window.location.href = 'boards.html';
  }

  // Логин
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');
    errorEl.textContent = '';

    if (!email || !password) {
      errorEl.textContent = 'Email and password are required.';
      return;
    }

    try {
      const response = await api.post('/auth/login', { email, password });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      // Сохраняем токены
      api.setTokens(data.access_token, data.refresh_token);
      // Перенаправление на доски (пока файла нет, но создадим позже)
      window.location.href = 'boards.html';
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });

  // Регистрация
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const passwordConfirm = document.getElementById('reg-password-confirm').value;
    const errorEl = document.getElementById('register-error');
    errorEl.textContent = '';

    if (!username || !email || !password || !passwordConfirm) {
      errorEl.textContent = 'All fields are required.';
      return;
    }
    if (password !== passwordConfirm) {
      errorEl.textContent = 'Passwords do not match.';
      return;
    }

    try {
      const response = await api.post('/auth/register', {
        username,
        email,
        password,
        password_confirm: passwordConfirm
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed');
      }

      // После регистрации автоматически логинимся (используем те же данные)
      const loginResponse = await api.post('/auth/login', { email, password });
      const loginData = await loginResponse.json();
      if (!loginResponse.ok) {
        throw new Error(loginData.detail || 'Auto-login failed');
      }
      api.setTokens(loginData.access_token, loginData.refresh_token);
      window.location.href = 'boards.html';
    } catch (err) {
      errorEl.textContent = err.message;
    }
  });
});