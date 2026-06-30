// Точка входа «Telegram Mini App» (внутри TG, в РФ через VPN).
// Авторизация — по initData от Telegram WebApp. Механизм приложения тот же.
import { createApp } from 'vue'
import App from '../core/App.vue'
import { api, setToken } from '../core/api.js'

const auth = {
  kind: 'miniapp',
  autoLogin: async () => {
    const tg = window.Telegram?.WebApp
    if (tg) tg.ready()
    const initData = tg?.initData
    if (!initData) throw new Error('Откройте приложение внутри Telegram')
    const { access_token } = await api.telegram(initData)
    setToken(access_token)
    return api.me()
  },
}

createApp(App, { auth }).mount('#app')
