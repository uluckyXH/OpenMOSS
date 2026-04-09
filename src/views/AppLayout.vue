<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { setupApi, webuiApi } from '@/api/client';
import type { WebUIVersionInfo } from '@/api/client';
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
} from '@/components/ui/sidebar';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
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
  Download,
  AlertTriangle,
  X,
  Loader2,
} from 'lucide-vue-next';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const localWebUIVersion = __VERSION__;

const showLogoutConfirm = ref(false);
const showUrlMissing = ref(false);

// WebUI 更新状态
const webuiVersion = ref<WebUIVersionInfo | null>(null);
const webuiUpdating = ref(false);
const showUpdateBanner = ref(false);

onMounted(async () => {
  try {
    const { data } = await setupApi.status();
    if (data.initialized && !data.has_external_url) {
      showUrlMissing.value = true;
    }
  } catch {
    // 静默失败
  }

  // 检查 WebUI 更新
  try {
    const { data } = await webuiApi.version();
    webuiVersion.value = data;
    if (data.update_available) {
      showUpdateBanner.value = true;
    }
  } catch {
    // 静默失败
  }
});

async function handleWebuiUpdate() {
  webuiUpdating.value = true;
  try {
    await webuiApi.update();
    // 更新成功，提示用户刷新
    webuiVersion.value = null;
    showUpdateBanner.value = false;
    // 延迟刷新
    setTimeout(() => window.location.reload(), 1500);
  } catch {
    webuiUpdating.value = false;
  }
}

function dismissUpdateBanner() {
  showUpdateBanner.value = false;
}

const menuItems = [
  { title: '仪表盘', icon: LayoutDashboard, path: '/dashboard' },
  { title: 'Agent 管理', icon: Users, path: '/agents' },
  { title: '任务管理', icon: ListTodo, path: '/tasks' },
  { title: '积分排行', icon: Trophy, path: '/scores' },
  { title: '活动日志', icon: ScrollText, path: '/logs' },
  { title: '审查记录', icon: FileSearch, path: '/reviews' },
  { title: '提示词管理', icon: BookText, path: '/prompts' },
  { title: '系统设置', icon: Settings, path: '/settings' },
];

function handleLogout() {
  auth.logout();
  router.push('/login');
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
          <div class="flex flex-col justify-center">
            <div class="font-bold text-base tracking-tight">OpenMOSS</div>
            <div class="flex flex-col items-start gap-1 mt-0.5">
              <span class="text-[11px] text-muted-foreground/60 leading-none">多 Agent 协作平台</span>
              <span
                class="text-[9px] font-medium px-1.5 py-0.5 rounded-md bg-blue-50 text-blue-600 border border-blue-200/60 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20 leading-none">WebUI
                v{{ localWebUIVersion }}</span>
            </div>
          </div>
        </div>
        <!-- 装饰线 -->
        <div class="h-[2px] rounded-full bg-gradient-to-r from-primary/30 via-primary/10 to-transparent" />
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel class="px-5 text-[10px] uppercase tracking-widest text-muted-foreground/50 font-semibold">
            导航</SidebarGroupLabel>
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

      <!-- WebUI 更新提示 Banner -->
      <Transition name="slide-down">
        <div v-if="showUpdateBanner && webuiVersion" class="px-4 pt-2">
          <!-- 升级提示 -->
          <div v-if="webuiVersion.update_type === 'upgrade'"
            class="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 dark:border-blue-900 dark:bg-blue-950/50">
            <Download class="h-4 w-4 shrink-0 text-blue-600 dark:text-blue-400" />
            <span class="flex-1 text-sm text-blue-800 dark:text-blue-200">
              🎉 WebUI <strong>v{{ webuiVersion.latest_version }}</strong> 可用
              <span v-if="webuiVersion.current_version" class="text-blue-600/60 dark:text-blue-400/60">
                (当前 v{{ webuiVersion.current_version }})
              </span>
            </span>
            <Button v-if="auth.isAuthenticated" size="sm" variant="outline"
              class="h-7 border-blue-300 text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:text-blue-300 dark:hover:bg-blue-900/50"
              :disabled="webuiUpdating" @click="handleWebuiUpdate">
              <Loader2 v-if="webuiUpdating" class="mr-1 h-3 w-3 animate-spin" />
              {{ webuiUpdating ? '更新中...' : '立即更新' }}
            </Button>
            <button class="text-blue-400 hover:text-blue-600 dark:hover:text-blue-300" @click="dismissUpdateBanner">
              <X class="h-3.5 w-3.5" />
            </button>
          </div>

          <!-- 回滚提示 -->
          <div v-else-if="webuiVersion.update_type === 'rollback'"
            class="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 dark:border-amber-900 dark:bg-amber-950/50">
            <AlertTriangle class="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
            <span class="flex-1 text-sm text-amber-800 dark:text-amber-200">
              ⚠️ 当前版本 v{{ webuiVersion.current_version }} 已被撤回
            </span>
            <Button v-if="auth.isAuthenticated" size="sm" variant="outline"
              class="h-7 border-amber-300 text-amber-700 hover:bg-amber-100 dark:border-amber-800 dark:text-amber-300 dark:hover:bg-amber-900/50"
              :disabled="webuiUpdating" @click="handleWebuiUpdate">
              <Loader2 v-if="webuiUpdating" class="mr-1 h-3 w-3 animate-spin" />
              {{ webuiUpdating ? '恢复中...' : `恢复到 v${webuiVersion.latest_version}` }}
            </Button>
            <button class="text-amber-400 hover:text-amber-600 dark:hover:text-amber-300" @click="dismissUpdateBanner">
              <X class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </Transition>

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

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
