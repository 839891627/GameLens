/**
 * 帧探·GameLens - 管理后台入口
 */

import { createApp } from 'vue';
import AdminApp from './AdminApp.vue';

// 创建并挂载应用
const app = createApp(AdminApp);
app.mount('#app');