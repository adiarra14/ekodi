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
    localStorage.setItem('ekodi_user', JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  };

  const register = async (email, name, password) => {
    const data = await authAPI.register({ email, name, password });
    localStorage.setItem('ekodi_token', data.token);
    localStorage.setItem('ekodi_user', JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem('ekodi_token');
    localStorage.removeItem('ekodi_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
