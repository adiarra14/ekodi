import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/voice-chat': 'http://localhost:8000',
      '/conversations': 'http://localhost:8000',
      '/tts': 'http://localhost:8000',
      '/feedback': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
