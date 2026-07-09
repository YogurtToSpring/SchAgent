import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const devApiProxy = env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8080'

  return {
    plugins: [vue()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: devApiProxy,
          changeOrigin: true
        }
      }
    }
  }
})
