import { createRouter, createWebHistory } from 'vue-router'
import WindowChat from '../views/windowChat.vue' 


const routes = [
  {
    path: '/',
    name: 'windowChat',
    component: WindowChat,
  },
  
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router