<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminConfigApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Save, Eye, EyeOff, RefreshCw, Copy, Loader2, Plus, Trash2 } from 'lucide-vue-next'
import { toast } from 'vue-sonner'

const loading = ref(true)
const saving = ref<string | null>(null)

// 配置数据
const projectName = ref('')
const registrationToken = ref('')
const allowRegistration = ref(true)
const notificationEnabled = ref(false)
const notificationChannels = ref<string[]>([])
const notificationEvents = ref<string[]>([])
const publicFeed = ref(false)
const feedRetentionDays = ref(7)
const workspaceRoot = ref('')
const externalUrl = ref('')

// 密码修改
const showPasswordForm = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

const allEvents = [
    { value: 'task_completed', label: '子任务完成' },
    { value: 'review_rejected', label: '审查驳回' },
    { value: 'all_done', label: '任务全部完成' },
    { value: 'patrol_alert', label: '巡查告警' },
]

onMounted(async () => {
    try {
        const res = await adminConfigApi.get()
        const cfg = res.data as Record<string, Record<string, unknown>>

        projectName.value = (cfg.project?.name as string) || ''
        registrationToken.value = (cfg.agent?.registration_token as string) || ''
        allowRegistration.value = (cfg.agent?.allow_registration as boolean) ?? true
        notificationEnabled.value = (cfg.notification?.enabled as boolean) ?? false
        notificationChannels.value = (cfg.notification?.channels as string[]) || []
        notificationEvents.value = (cfg.notification?.events as string[]) || []
        publicFeed.value = (cfg.webui?.public_feed as boolean) ?? false
        feedRetentionDays.value = (cfg.webui?.feed_retention_days as number) ?? 7
        workspaceRoot.value = (cfg.workspace?.root as string) || ''
        externalUrl.value = (cfg.server?.external_url as string) || ''
    } catch (e) {
        console.error('加载配置失败', e)
        showMessage('加载配置失败', 'error')
    } finally {
        loading.value = false
    }
})

function showMessage(msg: string, type: 'success' | 'error' = 'success') {
    if (type === 'success') {
        toast.success(msg)
    } else {
        toast.error(msg)
    }
}

async function saveSection(section: string) {
    saving.value = section
    try {
        let data: Record<string, unknown> = {}

        switch (section) {
            case 'project':
                data = {
                    project: { name: projectName.value },
                    workspace: { root: workspaceRoot.value },
                    server: { external_url: externalUrl.value },
                }
                break
            case 'agent':
                data = {
                    agent: {
                        registration_token: registrationToken.value,
                        allow_registration: allowRegistration.value,
                    }
                }
                break
            case 'notification':
                data = {
                    notification: {
                        enabled: notificationEnabled.value,
                        channels: notificationChannels.value.map(c => c.trim()).filter(c => c),
                        events: notificationEvents.value,
                    }
                }
                break
            case 'webui':
                data = {
                    webui: {
                        public_feed: publicFeed.value,
                        feed_retention_days: feedRetentionDays.value,
                    }
                }
                break
            case 'workspace':
                data = { workspace: { root: workspaceRoot.value } }
                break
            case 'server':
                data = { server: { external_url: externalUrl.value } }
                break
        }

        await adminConfigApi.update(data)
        showMessage('保存成功', 'success')
    } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } }
        showMessage(err.response?.data?.detail || '保存失败', 'error')
    } finally {
        saving.value = null
    }
}

async function handleChangePassword() {
    if (newPassword.value.length < 6) {
        showMessage('新密码至少 6 位', 'error')
        return
    }
    if (newPassword.value !== confirmPassword.value) {
        showMessage('两次输入的密码不一致', 'error')
        return
    }

    saving.value = 'password'
    try {
        await adminConfigApi.updatePassword(oldPassword.value, newPassword.value)
        showMessage('密码修改成功')
        showPasswordForm.value = false
        oldPassword.value = ''
        newPassword.value = ''
        confirmPassword.value = ''
    } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } }
        showMessage(err.response?.data?.detail || '密码修改失败', 'error')
    } finally {
        saving.value = null
    }
}

function toggleEvent(event: string) {
    const idx = notificationEvents.value.indexOf(event)
    if (idx >= 0) {
        notificationEvents.value.splice(idx, 1)
    } else {
        notificationEvents.value.push(event)
    }
}

function regenerateToken() {
    const chars = 'abcdef0123456789'
    let result = ''
    for (let i = 0; i < 32; i++) {
        result += chars[Math.floor(Math.random() * chars.length)]
    }
    registrationToken.value = result
}

async function copyText(text: string) {
    try {
        await navigator.clipboard.writeText(text)
        showMessage('已复制')
    } catch { /* silent */ }
}
</script>

<template>
    <div class="max-w-2xl">
        <!-- Loading -->
        <div v-if="loading" class="flex justify-center py-12">
            <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>

        <template v-else>
            <Tabs default-value="project" class="w-full">
                <TabsList class="grid w-full grid-cols-4">
                    <TabsTrigger value="project">项目</TabsTrigger>
                    <TabsTrigger value="security">安全</TabsTrigger>
                    <TabsTrigger value="notification">通知</TabsTrigger>
                    <TabsTrigger value="display">显示</TabsTrigger>
                </TabsList>

                <!-- ============================================================ -->
                <!-- Tab 1: 项目设置 -->
                <!-- ============================================================ -->
                <TabsContent value="project">
                    <Card>
                        <CardHeader>
                            <CardTitle class="text-base">项目设置</CardTitle>
                            <CardDescription>基本项目信息和工作目录配置</CardDescription>
                        </CardHeader>
                        <CardContent class="space-y-4">
                            <div class="space-y-2">
                                <Label for="s-project-name">项目名称</Label>
                                <Input id="s-project-name" v-model="projectName" />
                            </div>
                            <div class="space-y-2">
                                <Label for="s-workspace">工作目录</Label>
                                <Input id="s-workspace" v-model="workspaceRoot" placeholder="/path/to/workspace" />
                                <p class="text-xs text-muted-foreground">Agent 产出物的根目录路径</p>
                            </div>

                            <Separator />

                            <div class="space-y-2">
                                <Label for="s-external-url">服务访问地址</Label>
                                <Input id="s-external-url" v-model="externalUrl" placeholder="https://moss.example.com" />
                                <p class="text-xs text-muted-foreground">
                                    Agent 通过此地址下载工具脚本（task-cli.py）和技能配置（SKILL.md），并与任务系统通信。
                                    服务默认端口为 <code class="bg-muted px-1 py-0.5 rounded">6565</code>。
                                </p>
                                <div class="flex flex-col gap-1 mt-1">
                                    <div class="flex items-center gap-2">
                                        <code class="text-xs bg-muted px-2 py-1 rounded">https://moss.example.com</code>
                                        <span class="text-xs text-muted-foreground">← 反向代理</span>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <code class="text-xs bg-muted px-2 py-1 rounded">http://123.45.67.89:6565</code>
                                        <span class="text-xs text-muted-foreground">← IP + 端口</span>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <code class="text-xs bg-muted px-2 py-1 rounded">http://127.0.0.1:6565</code>
                                        <span class="text-xs text-muted-foreground">← 本地测试</span>
                                    </div>
                                </div>
                            </div>

                            <div class="flex justify-end">
                                <Button size="sm" @click="saveSection('project')" :disabled="!!saving">
                                    <Loader2 v-if="saving === 'project'" class="mr-1 h-3.5 w-3.5 animate-spin" />
                                    <Save v-else class="mr-1 h-3.5 w-3.5" />
                                    {{ saving === 'project' ? '保存中...' : '保存' }}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <!-- ============================================================ -->
                <!-- Tab 2: 安全设置 -->
                <!-- ============================================================ -->
                <TabsContent value="security">
                    <Card>
                        <CardHeader>
                            <CardTitle class="text-base">安全设置</CardTitle>
                            <CardDescription>管理员密码和 Agent 注册管理</CardDescription>
                        </CardHeader>
                        <CardContent class="space-y-4">
                            <!-- 密码修改 -->
                            <div>
                                <Button variant="outline" size="sm" @click="showPasswordForm = !showPasswordForm">
                                    <component :is="showPasswordForm ? EyeOff : Eye" class="mr-1 h-3.5 w-3.5" />
                                    {{ showPasswordForm ? '取消修改密码' : '修改管理员密码' }}
                                </Button>
                            </div>
                            <div v-if="showPasswordForm" class="space-y-3 rounded-lg border p-4">
                                <div class="space-y-2">
                                    <Label for="s-old-pwd">当前密码</Label>
                                    <Input id="s-old-pwd" v-model="oldPassword" type="password" />
                                </div>
                                <div class="space-y-2">
                                    <Label for="s-new-pwd">新密码</Label>
                                    <Input id="s-new-pwd" v-model="newPassword" type="password" placeholder="至少 6 位" />
                                </div>
                                <div class="space-y-2">
                                    <Label for="s-confirm-pwd">确认新密码</Label>
                                    <Input id="s-confirm-pwd" v-model="confirmPassword" type="password" />
                                </div>
                                <Button size="sm" @click="handleChangePassword" :disabled="saving === 'password'">
                                    {{ saving === 'password' ? '修改中...' : '确认修改' }}
                                </Button>
                            </div>

                            <Separator />

                            <!-- 注册令牌 -->
                            <div class="space-y-2">
                                <Label for="s-reg-token">Agent 注册令牌</Label>
                                <div class="flex gap-2">
                                    <Input id="s-reg-token" v-model="registrationToken"
                                        class="flex-1 font-mono text-sm" />
                                    <Button variant="outline" size="icon" @click="regenerateToken" title="重新生成">
                                        <RefreshCw class="h-4 w-4" />
                                    </Button>
                                    <Button variant="outline" size="icon" @click="copyText(registrationToken)"
                                        title="复制">
                                        <Copy class="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>

                            <!-- 自注册开关 -->
                            <div class="flex items-center justify-between rounded-lg border p-3">
                                <div>
                                    <Label>允许 Agent 自注册</Label>
                                    <p class="text-xs text-muted-foreground">关闭后只能由管理员创建 Agent</p>
                                </div>
                                <Switch v-model="allowRegistration" />
                            </div>

                            <div class="flex justify-end">
                                <Button size="sm" @click="saveSection('agent')" :disabled="!!saving">
                                    <Loader2 v-if="saving === 'agent'" class="mr-1 h-3.5 w-3.5 animate-spin" />
                                    <Save v-else class="mr-1 h-3.5 w-3.5" />
                                    {{ saving === 'agent' ? '保存中...' : '保存' }}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <!-- ============================================================ -->
                <!-- Tab 3: 通知设置 -->
                <!-- ============================================================ -->
                <TabsContent value="notification">
                    <Card>
                        <CardHeader>
                            <CardTitle class="text-base">通知设置</CardTitle>
                            <CardDescription>配置 Agent 通知渠道和触发事件</CardDescription>
                        </CardHeader>
                        <CardContent class="space-y-4">
                            <div class="flex items-center justify-between rounded-lg border p-3">
                                <div class="space-y-1">
                                    <Label>启用通知推送</Label>
                                    <p class="text-xs text-muted-foreground">Agent 将按配置的渠道发送通知</p>
                                </div>
                                <Switch v-model="notificationEnabled" />
                            </div>

                            <template v-if="notificationEnabled">
                                <div class="space-y-2">
                                    <Label>通知渠道</Label>
                                    <div class="space-y-2">
                                        <div v-for="(_, idx) in notificationChannels" :key="idx"
                                            class="flex items-center gap-2">
                                            <Input v-model="notificationChannels[idx]" class="flex-1 font-mono text-sm"
                                                placeholder="chat:oc_xxx 或 email:xxx@example.com" />
                                            <Button variant="ghost" size="icon"
                                                class="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
                                                @click="notificationChannels.splice(idx, 1)">
                                                <Trash2 class="h-3.5 w-3.5" />
                                            </Button>
                                        </div>
                                        <Button variant="outline" size="sm" class="w-full"
                                            @click="notificationChannels.push('')">
                                            <Plus class="mr-1 h-3.5 w-3.5" />
                                            添加渠道
                                        </Button>
                                    </div>
                                    <div class="space-y-1 text-xs text-muted-foreground">
                                        <p class="font-medium text-foreground/60">支持的渠道类型：</p>
                                        <p><code class="bg-muted px-1 py-0.5 rounded">chat:oc_xxx</code> — OpenClaw 群聊（将
                                            Agent 拉入群聊后可获取 chat_id）</p>
                                        <p><code class="bg-muted px-1 py-0.5 rounded">user:ou_xxx</code> — OpenClaw
                                            私聊（使用 open_id）</p>
                                        <p><code class="bg-muted px-1 py-0.5 rounded">email:xxx@example.com</code> —
                                            邮件通知（需 Agent 具备发送邮件的能力）</p>
                                    </div>
                                </div>

                                <div class="space-y-2">
                                    <Label>触发事件</Label>
                                    <div class="grid grid-cols-2 gap-2">
                                        <div v-for="event in allEvents" :key="event.value"
                                            class="flex items-center gap-2 rounded-lg border p-2 cursor-pointer hover:bg-muted/50 transition-colors"
                                            @click="toggleEvent(event.value)">
                                            <div class="h-4 w-4 rounded border flex items-center justify-center"
                                                :class="notificationEvents.includes(event.value) ? 'bg-primary border-primary' : ''">
                                                <svg v-if="notificationEvents.includes(event.value)"
                                                    class="h-3 w-3 text-primary-foreground" fill="none"
                                                    viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                                                    <path stroke-linecap="round" stroke-linejoin="round"
                                                        d="M5 13l4 4L19 7" />
                                                </svg>
                                            </div>
                                            <span class="text-sm">{{ event.label }}</span>
                                        </div>
                                    </div>
                                </div>
                            </template>

                            <div class="flex justify-end">
                                <Button size="sm" @click="saveSection('notification')" :disabled="!!saving">
                                    <Loader2 v-if="saving === 'notification'" class="mr-1 h-3.5 w-3.5 animate-spin" />
                                    <Save v-else class="mr-1 h-3.5 w-3.5" />
                                    {{ saving === 'notification' ? '保存中...' : '保存' }}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <!-- ============================================================ -->
                <!-- Tab 4: 显示设置 -->
                <!-- ============================================================ -->
                <TabsContent value="display">
                    <Card>
                        <CardHeader>
                            <CardTitle class="text-base">显示设置</CardTitle>
                            <CardDescription>WebUI 活动流和日志相关配置</CardDescription>
                        </CardHeader>
                        <CardContent class="space-y-4">
                            <div class="flex items-center justify-between rounded-lg border p-3">
                                <div class="space-y-1">
                                    <Label>活动流公开</Label>
                                    <p class="text-xs text-muted-foreground">开启后无需登录即可访问 <code
                                            class="bg-muted px-1 py-0.5 rounded">/feed</code> 页面，实时查看 Agent 活动动态</p>
                                </div>
                                <Switch v-model="publicFeed" />
                            </div>
                            <div class="space-y-2">
                                <Label for="s-retention">日志保留天数</Label>
                                <Input id="s-retention" v-model.number="feedRetentionDays" type="number" min="1"
                                    max="365" class="w-32" />
                                <p class="text-xs text-muted-foreground">超过此天数的请求日志将在启动时自动清理</p>
                            </div>
                            <div class="flex justify-end">
                                <Button size="sm" @click="saveSection('webui')" :disabled="!!saving">
                                    <Loader2 v-if="saving === 'webui'" class="mr-1 h-3.5 w-3.5 animate-spin" />
                                    <Save v-else class="mr-1 h-3.5 w-3.5" />
                                    {{ saving === 'webui' ? '保存中...' : '保存' }}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </template>
    </div>
</template>
