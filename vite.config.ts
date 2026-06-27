import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: resolve(__dirname, 'src'),
  build: {
    outDir: resolve(__dirname, 'web/static/dist'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/upload': 'http://localhost:5000',
      '/files': 'http://localhost:5000',
      '/delete-file': 'http://localhost:5000',
      '/delete-all-files': 'http://localhost:5000',
      '/validate': 'http://localhost:5000',
      '/validate-same-routes': 'http://localhost:5000',
      '/process': 'http://localhost:5000',
      '/status': 'http://localhost:5000',
      '/status-stream': { target: 'http://localhost:5000', changeOrigin: true },
      '/briefing': 'http://localhost:5000',
      '/animation': 'http://localhost:5000',
      '/temp': 'http://localhost:5000',
    },
  },
});
