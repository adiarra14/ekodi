import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Chat from './pages/Chat';
import ApiKeys from './pages/ApiKeys';
import Admin from './pages/Admin';
import './i18n';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Pages with navbar */}
          <Route element={<Layout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/api-keys" element={<ApiKeys />} />
            <Route path="/admin" element={<Admin />} />
          </Route>
          {/* Chat has its own full-screen layout */}
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
