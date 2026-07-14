class ApiClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  // Получение токена из localStorage
  getAccessToken() {
    return localStorage.getItem(AppConfig.TOKEN_KEY);
  }

  getRefreshToken() {
    return localStorage.getItem(AppConfig.REFRESH_TOKEN_KEY);
  }

  setTokens(access, refresh) {
    if (access) localStorage.setItem(AppConfig.TOKEN_KEY, access);
    if (refresh) localStorage.setItem(AppConfig.REFRESH_TOKEN_KEY, refresh);
  }

  clearTokens() {
    localStorage.removeItem(AppConfig.TOKEN_KEY);
    localStorage.removeItem(AppConfig.REFRESH_TOKEN_KEY);
  }

  // Обертка над fetch с автоматическим добавлением заголовков
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const token = this.getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      let response = await fetch(url, { ...options, headers });

      // Попытка автоматического обновления токена при 401
      if (response.status === 401 && this.getRefreshToken()) {
        const refreshed = await this.refreshAccessToken();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
          response = await fetch(url, { ...options, headers });
        } else {
          this.clearTokens();
          window.location.href = '/'; // или на страницу логина
          throw new Error('Session expired');
        }
      }

      return response;
    } catch (error) {
      if (error.message === 'Failed to fetch') {
        throw new Error('Network error. Please check your connection.');
      }
      throw error;
    }
  }

  async refreshAccessToken() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${this.baseURL}/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) return false;

      const data = await response.json();
      if (data.access_token) {
        localStorage.setItem(AppConfig.TOKEN_KEY, data.access_token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  // Удобные методы
  get(endpoint) {
    return this.request(endpoint);
  }

  post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  patch(endpoint, body) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  }

  delete(endpoint) {
    return this.request(endpoint, {
      method: 'DELETE',
    });
  }
}

// Глобальный экземпляр API
const api = new ApiClient(AppConfig.BASE_URL);