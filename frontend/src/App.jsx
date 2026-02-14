import { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import SplashScreen from './components/SplashScreen';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Chat from './pages/Chat';
import ApiKeys from './pages/ApiKeys';
import Admin from './pages/Admin';
import PartnerForm from './pages/PartnerForm';
import './i18n';

export default function App() {
  const [splashDone, setSplashDone] = useState(false);
  const handleSplashDone = useCallback(() => setSplashDone(true), []);

  return (
    <BrowserRouter>
      <AuthProvider>
        {!splashDone && <SplashScreen onDone={handleSplashDone} />}
        <Routes>
          {/* Pages with navbar */}
          <Route element={<Layout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/api-keys" element={<ApiKeys />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/partners" element={<PartnerForm />} />
          </Route>
          {/* Chat has its own full-screen layout */}
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
