<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { setupApi } from '@/api/client'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import {
  LayoutDashboard,
  ListTodo,
  Users,
  Trophy,
  ScrollText,
  FileSearch,
  BookText,
  Settings,
  LogOut,
  ShieldAlert,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const showLogoutConfirm = ref(false)
const showUrlMissing = ref(false)

onMounted(async () => {
  try {
    const { data } = await setupApi.status()
    if (data.initialized && !data.has_external_url) {
      showUrlMissing.value = true
    }
  } catch {
    // 静默失败
  }
})

const menuItems = [
  { title: '仪表盘', icon: LayoutDashboard, path: '/dashboard' },
  { title: '任务管理', icon: ListTodo, path: '/tasks' },
  { title: 'Agent', icon: Users, path: '/agents' },
  { title: '积分排行', icon: Trophy, path: '/scores' },
  { title: '活动日志', icon: ScrollText, path: '/logs' },
  { title: '审查记录', icon: FileSearch, path: '/reviews' },
  { title: '提示词管理', icon: BookText, path: '/prompts' },
  { title: '系统设置', icon: Settings, path: '/settings' },
  { title: '系统巡查', icon: ShieldAlert, path: '/patrol' },
]

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <SidebarProvider>
    <Sidebar>
      <SidebarHeader class="px-5 pt-6 pb-4">
        <!-- Logo 区域 -->
        <div class="flex items-center gap-3.5 mb-3">
          <div
            class="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground text-base font-bold shadow-[var(--shadow-sm)]">
            M
          </div>
          <div>
            <div class="font-bold text-base tracking-tight">OpenMOSS</div>
            <div class="text-[11px] text-muted-foreground/60">多 Agent 协作平台</div>
          </div>
        </div>
        <!-- 装饰线 -->
        <div class="h-[2px] rounded-full bg-gradient-to-r from-primary/30 via-primary/10 to-transparent" />
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel class="px-5 text-[10px] uppercase tracking-widest text-muted-foreground/50 font-semibold">导航</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu class="space-y-1 px-2">
              <SidebarMenuItem v-for="item in menuItems" :key="item.path">
                <SidebarMenuButton as-child :is-active="route.path === item.path">
                  <router-link :to="item.path"
                    class="group/link transition-all duration-150 hover:translate-x-0.5 !py-5 !gap-4 !rounded-xl">
                    <component :is="item.icon" class="h-6 w-6 shrink-0 transition-opacity duration-150"
                      :class="route.path === item.path ? 'opacity-100' : 'opacity-50 group-hover/link:opacity-80'" />
                    <span class="text-base">{{ item.title }}</span>
                  </router-link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter class="px-4 pb-5 pt-3">
        <Button variant="ghost" size="sm"
          class="w-full justify-start gap-2 text-muted-foreground hover:text-destructive transition-colors duration-150 h-9"
          @click="showLogoutConfirm = true">
          <LogOut class="h-4 w-4" />
          <span class="text-sm">退出登录</span>
        </Button>
      </SidebarFooter>
    </Sidebar>

    <SidebarInset>
      <header class="flex h-14 items-center gap-2 border-b px-4 bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <SidebarTrigger />
        <Separator orientation="vertical" class="h-4" />
        <h1 class="text-sm font-medium">
          {{menuItems.find(i => i.path === route.path)?.title || ''}}
        </h1>
      </header>
      <main class="flex-1 p-6">
        <router-view />
      </main>
    </SidebarInset>
  </SidebarProvider>

  <!-- 退出登录确认弹窗 -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showLogoutConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showLogoutConfirm = false" />
        <!-- 弹窗 -->
        <div
          class="relative z-10 w-full max-w-sm rounded-2xl border bg-background/95 backdrop-blur-xl p-6 shadow-[var(--shadow-lg)] animate-in fade-in zoom-in-95 duration-200">
          <div class="space-y-2 text-center">
            <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <LogOut class="h-5 w-5 text-muted-foreground" />
            </div>
            <h2 class="text-lg font-semibold">确认退出</h2>
            <p class="text-sm text-muted-foreground">退出后需要重新输入管理员密码登录</p>
          </div>
          <div class="mt-6 flex gap-3">
            <Button variant="outline" class="flex-1" @click="showLogoutConfirm = false">取消</Button>
            <Button variant="destructive" class="flex-1" @click="handleLogout">确认退出</Button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- 服务地址未配置提示弹窗 -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showUrlMissing" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showUrlMissing = false" />
        <div
          class="relative z-10 w-full max-w-sm rounded-2xl border bg-background/95 backdrop-blur-xl p-6 shadow-[var(--shadow-lg)] animate-in fade-in zoom-in-95 duration-200">
          <div class="space-y-2 text-center">
            <div class="text-3xl mb-2">⚠️</div>
            <h2 class="text-lg font-semibold">请配置服务访问地址</h2>
            <p class="text-sm text-muted-foreground">
              OpenMOSS 需要一个外网可访问的地址，用于：
            </p>
            <ul class="text-sm text-muted-foreground text-left ml-4 list-disc space-y-1">
              <li>Agent 下载工具脚本</li>
              <li>Agent 对接任务系统</li>
              <li>生成 Agent 入驻 Prompt</li>
            </ul>
            <p class="text-xs text-muted-foreground mt-2">
              示例：https://moss.example.com
            </p>
          </div>
          <div class="mt-6 flex gap-3">
            <Button variant="outline" class="flex-1" @click="showUrlMissing = false">稍后再说</Button>
            <Button class="flex-1" @click="showUrlMissing = false; router.push('/settings')">前往设置</Button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
