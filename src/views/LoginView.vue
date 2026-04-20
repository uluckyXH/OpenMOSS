<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const password = ref('');
const loading = ref(false);
const error = ref('');

async function handleLogin() {
    if (!password.value) {
        error.value = '请输入密码';
        return;
    }
    loading.value = true;
    error.value = '';
    try {
        await auth.login(password.value);
        // 初始化完成后跳转提示词管理，否则跳转仪表盘
        const target = route.query.from === 'setup' ? '/prompts' : '/dashboard';
        router.push(target);
    } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } };
        error.value = err.response?.data?.detail || '登录失败，请检查密码';
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="login-page relative flex min-h-screen items-center justify-center bg-background overflow-hidden">

        <!-- 动态渐变光晕 -->
        <div class="login-orb login-orb-1" />
        <div class="login-orb login-orb-2" />
        <div class="login-orb login-orb-3" />

        <!-- 网格叠加 -->
        <div class="login-grid absolute inset-0" />

        <!-- 卡片 -->
        <Card
            class="login-card relative z-10 w-full max-w-sm shadow-[var(--shadow-lg)] rounded-2xl border-border/40 bg-background/80 backdrop-blur-xl">
            <CardHeader class="text-center pb-2">
                <div
                    class="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground text-2xl font-bold shadow-[var(--shadow-md)]">
                    M
                </div>
                <CardTitle class="text-2xl font-bold tracking-tight">OpenMOSS</CardTitle>
                <CardDescription class="text-muted-foreground/70">多Agent协同、自组织自修复自进化的AI公司操作系统</CardDescription>
            </CardHeader>
            <CardContent class="pt-2">
                <form @submit.prevent="handleLogin" class="space-y-5">
                    <div class="space-y-2">
                        <Label for="password" class="text-xs font-medium text-muted-foreground">管理员密码</Label>
                        <Input id="password" v-model="password" type="password" placeholder="请输入管理员密码"
                            :disabled="loading" @keyup.enter="handleLogin"
                            class="h-11 rounded-xl bg-muted/30 border-border/50 focus:ring-2 focus:ring-primary/20 focus:border-primary/30 transition-all duration-200 placeholder:text-muted-foreground/40" />
                    </div>
                    <p v-if="error"
                        class="text-sm text-destructive bg-destructive/5 rounded-lg px-3 py-2 border border-destructive/10">
                        {{ error }}
                    </p>
                    <Button type="submit"
                        class="w-full h-11 rounded-xl text-sm font-medium transition-all duration-200 hover:scale-[1.02] hover:shadow-md active:scale-[0.98]"
                        :disabled="loading">
                        {{ loading ? '登录中...' : '登 录' }}
                    </Button>
                    <details class="group text-center">
                        <summary
                            class="text-[11px] text-muted-foreground/40 cursor-pointer hover:text-muted-foreground/60 transition-colors select-none list-none [&::-webkit-details-marker]:hidden">
                            忘记密码？
                        </summary>
                        <div
                            class="mt-2 rounded-xl border border-border/30 bg-muted/20 backdrop-blur-sm p-3 text-left text-xs text-muted-foreground/70 space-y-1">
                            <p>1. 编辑服务器上的 <code
                                    class="rounded-md bg-muted/50 px-1.5 py-0.5 text-[11px]">config.yaml</code></p>
                            <p>2. 将 <code
                                    class="rounded-md bg-muted/50 px-1.5 py-0.5 text-[11px]">admin.password</code>
                                值改为新的明文密码</p>
                            <p>3. 重启服务，系统会自动加密处理</p>
                        </div>
                    </details>
                </form>
            </CardContent>
        </Card>

        <!-- 底部版本号 -->
        <div class="absolute bottom-6 text-[10px] text-muted-foreground/25 tracking-wider z-10">
            OpenMOSS v1.0
        </div>
    </div>
</template>

<style scoped>
/* 入场动画 */
.login-card {
    animation: card-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes card-in {
    from {
        opacity: 0;
        transform: translateY(20px) scale(0.96);
    }

    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

/* 网格背景 */
.login-grid {
    background-image:
        linear-gradient(rgb(0 0 0 / 0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgb(0 0 0 / 0.02) 1px, transparent 1px);
    background-size: 32px 32px;
    mask-image: radial-gradient(ellipse 70% 70% at 50% 50%, black 30%, transparent 100%);
}

:global(.dark) .login-grid {
    background-image:
        linear-gradient(rgb(255 255 255 / 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgb(255 255 255 / 0.025) 1px, transparent 1px);
}

/* 渐变光晕球 */
.login-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.15;
    animation: orb-float 12s ease-in-out infinite alternate;
}

.login-orb-1 {
    width: 400px;
    height: 400px;
    background: #818cf8;
    top: -10%;
    right: -5%;
    animation-delay: 0s;
}

.login-orb-2 {
    width: 350px;
    height: 350px;
    background: #06b6d4;
    bottom: -10%;
    left: -5%;
    animation-delay: -4s;
}

.login-orb-3 {
    width: 250px;
    height: 250px;
    background: #f59e0b;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    animation-delay: -8s;
    opacity: 0.08;
}

@keyframes orb-float {
    0% {
        transform: translate(0, 0) scale(1);
    }

    100% {
        transform: translate(30px, -20px) scale(1.1);
    }
}

/* 暗色模式光晕更柔和 */
:global(.dark) .login-orb {
    opacity: 0.08;
    filter: blur(100px);
}
</style>