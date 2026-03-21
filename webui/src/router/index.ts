import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { setupApi } from '@/api/client'

// 缓存初始化状态，避免每次路由跳转都请求
let _setupChecked = false
let _isInitialized = true // 默认 true，避免闪烁

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/setup',
      name: 'setup',
      component: () => import('@/views/SetupView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/feed',
      name: 'feed',
      component: () => import('@/views/FeedView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/views/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/dashboard',
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/views/TasksView.vue'),
        },
        {
          path: 'patrol',
          name: 'patrol',
          component: () => import('@/views/PatrolView.vue'),
        },
        {
          path: 'agents',
          name: 'agents',
          component: () => import('@/views/AgentsView.vue'),
        },
        {
          path: 'scores',
          name: 'scores',
          component: () => import('@/views/ScoresView.vue'),
        },
        {
          path: 'logs',
          name: 'logs',
          component: () => import('@/views/LogsView.vue'),
        },
        {
          path: 'reviews',
          name: 'reviews',
          component: () => import('@/views/ReviewsView.vue'),
        },
        {
          path: 'prompts',
          name: 'prompts',
          component: () => import('@/views/PromptsView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
        },
      ],
    },
  ],
})

// 路由守卫：初始化检查 + 登录检查
router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // 检查初始化状态（仅一次）
  if (!_setupChecked) {
    try {
      const { data } = await setupApi.status()
      _isInitialized = data.initialized
    } catch {
      // 接口不存在或出错，视为已初始化（兼容旧版本）
      _isInitialized = true
    }
    _setupChecked = true
  }

  // 未初始化 → 强制跳转 /setup
  if (!_isInitialized && to.name !== 'setup') {
    return { name: 'setup' }
  }
  // 已初始化 → 不允许访问 /setup
  if (_isInitialized && to.name === 'setup') {
    return { name: 'login' }
  }

  // 原有的登录检查
  if (to.meta.requiresAuth !== false && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
})

export default router

/** 重置初始化状态缓存（初始化完成后调用） */
export function resetSetupCache() {
  _setupChecked = false
  _isInitialized = true
}
