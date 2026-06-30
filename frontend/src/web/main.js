// Точка входа «сайт» (без VPN). Авторизация — логин/пароль.
import { createApp } from 'vue'
import App from '../core/App.vue'

const auth = {
  kind: 'web',
  // На сайте автologина нет — пользователь входит формой.
  autoLogin: async () => null,
}

createApp(App, { auth }).mount('#app')
