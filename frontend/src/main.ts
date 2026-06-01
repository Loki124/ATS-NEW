import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import App from './App.vue'
import router from './router'
import './index.css'

// Ant Design Vue theme configuration
import { ThemeConfig } from 'ant-design-vue/es/config-provider/context'

const theme: ThemeConfig = {
  token: {
    colorPrimary: '#FBCE5B',
  },
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Antd, { theme })

app.mount('#app')