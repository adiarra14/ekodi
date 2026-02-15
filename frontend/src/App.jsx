import { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import SplashScreen from './components/SplashScreen';
import ConsentBanner from './components/ConsentBanner';
import ServerBusyBanner from './components/ServerBusyBanner';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import VerifyEmail from './pages/VerifyEmail';
import Chat from './pages/Chat';
import ApiKeys from './pages/ApiKeys';
import Admin from './pages/Admin';
import PartnerForm from './pages/PartnerForm';
import Privacy from './pages/Privacy';
import UserSettings from './pages/UserSettings';
import './i18n';

export default function App() {
  const [splashDone, setSplashDone] = useState(false);
  const handleSplashDone = useCallback(() => setSplashDone(true), []);

  return (
    <BrowserRouter>
      <AuthProvider>
        {!splashDone && <SplashScreen onDone={handleSplashDone} />}
        <Routes>
          {/* ── Public pages (with website navbar) ── */}
          <Route element={<Layout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/partners" element={<PartnerForm />} />
            <Route path="/privacy" element={<Privacy />} />
          </Route>

          {/* ── Auth pages (no navbar, standalone) ── */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password/:token" element={<ResetPassword />} />
          <Route path="/verify/:token" element={<VerifyEmail />} />

          {/* ── App pages (own layout, no website navbar) ── */}
          <Route path="/chat" element={<Chat />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/api-keys" element={<ApiKeys />} />
          <Route path="/settings" element={<UserSettings />} />
        </Routes>
        <ConsentBanner />
        <ServerBusyBanner />
      </AuthProvider>
    </BrowserRouter>
  );
}
