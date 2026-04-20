<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { setupApi } from '@/api/client';
import { clipboardCopy } from '@/lib/clipboard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { ChevronRight, ChevronLeft, Check, Copy, RefreshCw } from 'lucide-vue-next';


// 向导步骤
const currentStep = ref(0);
const totalSteps = 5;
const loading = ref(false);
const error = ref('');
const showRegistrationToken = ref(false);
const resultToken = ref('');
const alreadyInitialized = ref(false);
const pageLoading = ref(true);

onMounted(async () => {
    try {
        const { data } = await setupApi.status();
        if (data.initialized) {
            alreadyInitialized.value = true;
        }
    } catch {
        // 接口异常，允许继续
    } finally {
        pageLoading.value = false;
    }
});

// 表单数据
const form = ref({
    adminPassword: '',
    confirmPassword: '',
    projectName: 'OpenMOSS',
    workspaceRoot: '',
    registrationToken: generateToken(),
    externalUrl: '',
    notificationChannels: '',
});
// Switch 状态独立声明（reka-ui Switch 对嵌套 ref 属性兼容性差）
const allowRegistration = ref(true);
const notificationEnabled = ref(false);

function generateToken() {
    const chars = 'abcdef0123456789';
    let result = '';
    for (let i = 0; i < 32; i++) {
        result += chars[Math.floor(Math.random() * chars.length)];
    }
    return result;
}

function regenerateToken() {
    form.value.registrationToken = generateToken();
}

async function copyToken(text: string) {
    try {
        await clipboardCopy(text);
    } catch {
        // 静默失败
    }
}

// 步骤验证
const stepErrors = computed(() => {
    const errors: Record<number, string> = {};

    // Step 0: 密码
    if (currentStep.value >= 0 && form.value.adminPassword.length > 0 && form.value.adminPassword.length < 6) {
        errors[0] = '密码至少 6 位';
    }
    if (currentStep.value >= 0 && form.value.confirmPassword && form.value.adminPassword !== form.value.confirmPassword) {
        errors[0] = '两次输入的密码不一致';
    }

    // Step 1: 项目信息
    if (currentStep.value >= 1 && form.value.projectName.length === 0) {
        errors[1] = '请输入项目名称';
    }

    return errors;
});

const canProceed = computed(() => {
    switch (currentStep.value) {
        case 0:
            return form.value.adminPassword.length >= 6
                && form.value.adminPassword === form.value.confirmPassword;
        case 1:
            return form.value.projectName.length > 0 && form.value.workspaceRoot.length > 0;
        case 2:
            return form.value.registrationToken.length > 0;
        case 3: // 服务地址（可跳过）
            return true;
        case 4: // 通知（可跳过）
            return true;
        default:
            return false;
    }
});

function nextStep() {
    if (currentStep.value < totalSteps - 1 && canProceed.value) {
        currentStep.value++;
        error.value = '';
    }
}

function prevStep() {
    if (currentStep.value > 0) {
        currentStep.value--;
        error.value = '';
    }
}

async function handleSubmit() {
    if (!canProceed.value) return;

    loading.value = true;
    error.value = '';

    try {
        // 解析通知渠道
        const channels = form.value.notificationChannels
            .split('\n')
            .map(c => c.trim())
            .filter(c => c.length > 0);

        const res = await setupApi.initialize({
            admin_password: form.value.adminPassword,
            project_name: form.value.projectName,
            workspace_root: form.value.workspaceRoot,
            registration_token: form.value.registrationToken,
            allow_registration: allowRegistration.value,
            external_url: form.value.externalUrl || undefined,
            notification: notificationEnabled.value ? {
                enabled: true,
                channels,
                events: ['task_completed', 'review_rejected', 'all_done', 'patrol_alert'],
            } : undefined,
        });

        resultToken.value = res.data.registration_token;
        showRegistrationToken.value = true;
    } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } };
        error.value = err.response?.data?.detail || '初始化失败，请重试';
    } finally {
        loading.value = false;
    }
}

function goToLogin() {
    // 初始化完成后跳转登录，带 from=setup 标记以便登录后跳转到提示词管理
    window.location.href = '/login?from=setup';
}

const steps = [
    { title: '管理员密码', desc: '设置管理员登录密码' },
    { title: '项目信息', desc: '配置项目名称和工作目录' },
    { title: 'Agent 注册', desc: '设置 Agent 注册令牌' },
    { title: '服务地址', desc: '配置 Agent 对接的服务访问地址' },
    { title: '通知渠道', desc: '配置消息通知（可跳过）' },
];
</script>

<template>
    <div class="flex min-h-screen items-center justify-center bg-background p-4">
        <!-- 加载中 -->
        <div v-if="pageLoading" class="flex justify-center py-12">
            <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>

        <!-- 已初始化提示 -->
        <Card v-else-if="alreadyInitialized" class="w-full max-w-md">
            <CardHeader class="text-center">
                <div
                    class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 text-amber-600 dark:bg-amber-900 dark:text-amber-400">
                    <Check class="h-6 w-6" />
                </div>
                <CardTitle class="text-xl">系统已初始化</CardTitle>
                <CardDescription>初始化向导仅在首次部署时可用。</CardDescription>
            </CardHeader>
            <CardContent class="space-y-3">
                <p class="text-sm text-muted-foreground text-center">
                    如需修改配置，请登录后在「系统设置」中操作。
                </p>
                <Button class="w-full" @click="$router.push('/login')">
                    前往登录
                    <ChevronRight class="ml-1 h-4 w-4" />
                </Button>
            </CardContent>
        </Card>

        <!-- 初始化完成弹窗 -->
        <Card v-else-if="showRegistrationToken" class="w-full max-w-md">
            <CardHeader class="text-center">
                <div
                    class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-900 dark:text-emerald-400">
                    <Check class="h-6 w-6" />
                </div>
                <CardTitle class="text-xl">初始化完成！</CardTitle>
                <CardDescription>请妥善保存以下 Agent 注册令牌</CardDescription>
            </CardHeader>
            <CardContent class="space-y-4">
                <div class="rounded-lg border bg-muted/50 p-4">
                    <Label class="text-xs text-muted-foreground">Agent 注册令牌</Label>
                    <div class="mt-1 flex items-center gap-2">
                        <code class="flex-1 text-sm font-mono break-all">{{ resultToken }}</code>
                        <Button variant="ghost" size="icon" @click="copyToken(resultToken)" title="复制">
                            <Copy class="h-4 w-4" />
                        </Button>
                    </div>
                    <p class="mt-2 text-xs text-muted-foreground">
                        Agent 注册时需要此令牌。你可以在「系统设置」中随时修改。
                    </p>
                </div>
                <p class="mt-3 text-xs text-muted-foreground text-center">
                    登录后可在「提示词管理」中快速创建 Agent 提示词并对接。
                </p>
                <Button class="w-full" @click="goToLogin">
                    前往登录
                    <ChevronRight class="ml-1 h-4 w-4" />
                </Button>
            </CardContent>
        </Card>

        <!-- 向导主体 -->
        <Card v-else class="w-full max-w-lg">
            <CardHeader class="text-center">
                <div
                    class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground text-xl font-bold">
                    M
                </div>
                <CardTitle class="text-2xl">欢迎使用 OpenMOSS</CardTitle>
                <CardDescription>多Agent协同、自组织自修复自进化的AI公司操作系统 — 初始化设置</CardDescription>
            </CardHeader>

            <CardContent>
                <div class="mb-6 flex items-center justify-center gap-2">
                    <template v-for="(step, i) in steps" :key="i">
                        <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium transition-colors"
                            :class="i < currentStep
                                ? 'bg-primary text-primary-foreground'
                                : i === currentStep
                                    ? 'bg-primary text-primary-foreground ring-2 ring-primary/30'
                                    : 'bg-muted text-muted-foreground'">
                            <Check v-if="i < currentStep" class="h-3.5 w-3.5" />
                            <span v-else>{{ i + 1 }}</span>
                        </div>
                        <div v-if="i < steps.length - 1" class="h-px w-8 bg-border" />
                    </template>
                </div>

                <p class="mb-4 text-center text-sm text-muted-foreground">
                    {{ steps[currentStep]?.desc }}
                </p>

                <!-- Step 0: 密码 -->
                <div v-if="currentStep === 0" class="space-y-4">
                    <div class="space-y-2">
                        <Label for="admin-password">管理员密码</Label>
                        <Input id="admin-password" v-model="form.adminPassword" type="password" placeholder="至少 6 位" />
                    </div>
                    <div class="space-y-2">
                        <Label for="confirm-password">确认密码</Label>
                        <Input id="confirm-password" v-model="form.confirmPassword" type="password" placeholder="再次输入密码"
                            @keyup.enter="nextStep" />
                    </div>
                    <p v-if="stepErrors[0]" class="text-sm text-destructive">{{ stepErrors[0] }}</p>
                </div>

                <!-- Step 1: 项目信息 -->
                <div v-if="currentStep === 1" class="space-y-4">
                    <div class="space-y-2">
                        <Label for="project-name">项目名称</Label>
                        <Input id="project-name" v-model="form.projectName" placeholder="OpenMOSS" />
                    </div>
                    <div class="space-y-2">
                        <Label for="workspace-root">工作目录</Label>
                        <Input id="workspace-root" v-model="form.workspaceRoot"
                            placeholder="例如：/home/openclaw/workspace" />
                        <p class="text-xs text-muted-foreground">
                            部署 OpenClaw 服务器上的一个共享目录路径，所有 Agent 都会在此目录下读写产出物。请确保该路径在服务器上已存在且 Agent 进程有读写权限。
                        </p>
                    </div>
                </div>

                <!-- Step 2: Agent 注册 -->
                <div v-if="currentStep === 2" class="space-y-4">
                    <div class="space-y-2">
                        <Label for="reg-token">注册令牌</Label>
                        <div class="flex gap-2">
                            <Input id="reg-token" v-model="form.registrationToken" class="flex-1 font-mono text-sm" />
                            <Button variant="outline" size="icon" @click="regenerateToken" title="重新生成">
                                <RefreshCw class="h-4 w-4" />
                            </Button>
                            <Button variant="outline" size="icon" @click="copyToken(form.registrationToken)" title="复制">
                                <Copy class="h-4 w-4" />
                            </Button>
                        </div>
                        <p class="text-xs text-muted-foreground">Agent 注册时需要此令牌来验证身份</p>
                    </div>
                    <div class="flex items-center justify-between rounded-lg border p-3">
                        <div>
                            <Label>允许 Agent 自注册</Label>
                            <p class="text-xs text-muted-foreground">关闭后只能由管理员手动创建 Agent</p>
                        </div>
                        <Switch v-model="allowRegistration" />
                    </div>
                </div>

                <!-- Step 3: 服务地址 -->
                <div v-if="currentStep === 3" class="space-y-4">
                    <div class="space-y-2">
                        <Label for="external-url">🌐 服务访问地址</Label>
                        <Input id="external-url" v-model="form.externalUrl"
                            placeholder="https://moss.example.com" />
                    </div>

                    <div class="rounded-lg border bg-muted/30 p-4 space-y-3">
                        <div>
                            <p class="text-sm font-medium">💡 这是什么？</p>
                            <p class="text-xs text-muted-foreground mt-1">
                                你的 AI Agent 需要通过这个地址来：
                            </p>
                            <ul class="text-xs text-muted-foreground mt-1 ml-4 list-disc space-y-0.5">
                                <li>下载工作工具（task-cli.py）</li>
                                <li>获取技能配置（SKILL.md）</li>
                                <li>与任务系统通信、领取和提交任务</li>
                            </ul>
                        </div>
                        <div>
                            <p class="text-sm font-medium">📝 填写说明</p>
                            <p class="text-xs text-muted-foreground mt-1">
                                请填写本服务器可从外网访问的完整地址。服务默认端口为
                                <code class="bg-muted px-1 py-0.5 rounded">6565</code>。
                            </p>
                            <div class="flex flex-col gap-1 mt-2">
                                <div class="flex items-center gap-2">
                                    <code class="text-xs bg-muted px-2 py-1 rounded">https://moss.example.com</code>
                                    <span class="text-xs text-muted-foreground">← 使用反向代理（Nginx/Caddy）</span>
                                </div>
                                <div class="flex items-center gap-2">
                                    <code class="text-xs bg-muted px-2 py-1 rounded">http://123.45.67.89:6565</code>
                                    <span class="text-xs text-muted-foreground">← 直接用 IP + 端口</span>
                                </div>
                                <div class="flex items-center gap-2">
                                    <code class="text-xs bg-muted px-2 py-1 rounded">http://127.0.0.1:6565</code>
                                    <span class="text-xs text-muted-foreground">← 本地测试用</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <p class="text-xs text-muted-foreground">
                        ⏩ 还没准备好？可以跳过，稍后在「系统设置」中配置
                    </p>
                </div>

                <!-- Step 4: 通知 -->
                <div v-if="currentStep === 4" class="space-y-4">
                    <div class="flex items-center justify-between rounded-lg border p-3">
                        <div>
                            <Label>启用通知推送</Label>
                            <p class="text-xs text-muted-foreground">Agent 完成任务、审查驳回等事件时发送通知</p>
                        </div>
                        <Switch v-model="notificationEnabled" />
                    </div>

                    <div v-if="notificationEnabled" class="space-y-2">
                        <Label for="channels">通知渠道</Label>
                        <textarea id="channels" v-model="form.notificationChannels"
                            class="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            placeholder="每行一个，格式：类型:ID&#10;例如：chat:oc_xxx" />
                        <p class="text-xs text-muted-foreground">
                            此项可以稍后在「系统设置」中配置
                        </p>
                    </div>
                </div>

                <!-- 错误提示 -->
                <p v-if="error" class="mt-4 text-sm text-destructive">{{ error }}</p>

                <!-- 导航按钮 -->
                <div class="mt-6 flex justify-between">
                    <Button v-if="currentStep > 0" variant="outline" @click="prevStep">
                        <ChevronLeft class="mr-1 h-4 w-4" />
                        上一步
                    </Button>
                    <div v-else />

                    <Button v-if="currentStep < totalSteps - 1" @click="nextStep" :disabled="!canProceed">
                        下一步
                        <ChevronRight class="ml-1 h-4 w-4" />
                    </Button>
                    <Button v-else @click="handleSubmit" :disabled="loading || !canProceed">
                        {{ loading ? '正在初始化...' : '完成设置' }}
                        <Check v-if="!loading" class="ml-1 h-4 w-4" />
                    </Button>
                </div>
            </CardContent>
        </Card>
    </div>
</template>
