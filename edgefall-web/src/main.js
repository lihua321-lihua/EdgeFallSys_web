/**
 * 应用入口 - Vue实例创建、插件注册、全局初始化
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './assets/styles/variables.css'
import './assets/styles/global.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { size: 'default' })
app.mount('#app')