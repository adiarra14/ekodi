import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('ekodi_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('ekodi_token');
    if (token) {
      authAPI
        .me()
        .then((u) => {
          setUser(u);
          localStorage.setItem('ekodi_user', JSON.stringify(u));
        })
        .catch(() => {
          localStorage.removeItem('ekodi_token');
          localStorage.removeItem('ekodi_refresh_token');
          localStorage.removeItem('ekodi_user');
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const data = await authAPI.login({ email, password });
    localStorage.setItem('ekodi_token', data.token);
    localStorage.setItem('ekodi_refresh_token', data.refresh_token);
    localStorage.setItem('ekodi_user', JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  };

  const register = async (email, name, password, consent = false, captcha_token = null) => {
    const data = await authAPI.register({ email, name, password, consent, captcha_token });
    localStorage.setItem('ekodi_token', data.token);
    localStorage.setItem('ekodi_refresh_token', data.refresh_token);
    localStorage.setItem('ekodi_user', JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try { await authAPI.logout(); } catch { /* ignore */ }
    localStorage.removeItem('ekodi_token');
    localStorage.removeItem('ekodi_refresh_token');
    localStorage.removeItem('ekodi_user');
    setUser(null);
  };

  const updateUser = (newUser) => {
    setUser(newUser);
    localStorage.setItem('ekodi_user', JSON.stringify(newUser));
  };

  const isStaff = user && ['superadmin', 'admin', 'support', 'marketing', 'finance', 'moderator', 'developer'].includes(user.role);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateUser, isStaff }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
