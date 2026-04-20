<script setup lang="ts">
import { useRouter } from 'vue-router';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

const router = useRouter();

function goHome() {
    router.push('/dashboard');
}

function goBack() {
    // 如果有浏览历史则返回，否则跳转首页
    if (window.history.length > 1) {
        router.back();
    } else {
        goHome();
    }
}
</script>

<template>
    <div class="notfound-page relative flex min-h-screen items-center justify-center bg-background overflow-hidden">

        <!-- 动态渐变光晕 -->
        <div class="nf-orb nf-orb-1" />
        <div class="nf-orb nf-orb-2" />
        <div class="nf-orb nf-orb-3" />

        <!-- 网格叠加 -->
        <div class="nf-grid absolute inset-0" />

        <!-- 卡片 -->
        <Card
            class="nf-card relative z-10 w-full max-w-md shadow-[var(--shadow-lg)] rounded-2xl border-border/40 bg-background/80 backdrop-blur-xl">
            <CardContent class="flex flex-col items-center py-12 px-8">
                <!-- 错误码 -->
                <div class="nf-code relative mb-2 select-none">
                    <span
                        class="text-[120px] font-black leading-none tracking-tighter bg-gradient-to-br from-primary/80 via-primary/50 to-primary/20 bg-clip-text text-transparent">
                        404
                    </span>
                    <!-- 浮动装饰圆点 -->
                    <div
                        class="absolute -top-2 -right-3 h-4 w-4 rounded-full bg-chart-1/60 animate-bounce [animation-duration:2s]" />
                    <div
                        class="absolute bottom-4 -left-2 h-3 w-3 rounded-full bg-chart-2/50 animate-bounce [animation-duration:2.5s] [animation-delay:0.3s]" />
                </div>

                <!-- 标题 -->
                <h1 class="nf-title text-xl font-bold tracking-tight text-foreground mb-2">
                    页面未找到
                </h1>

                <!-- 描述 -->
                <p class="nf-desc text-sm text-muted-foreground/70 text-center mb-8 max-w-xs leading-relaxed">
                    你访问的页面不存在或已被移除，请检查地址是否正确。
                </p>

                <!-- 操作按钮 -->
                <div class="nf-actions flex gap-3 w-full max-w-xs">
                    <Button variant="outline" @click="goBack"
                        class="flex-1 h-11 rounded-xl text-sm font-medium transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] border-border/50">
                        ← 返回上一页
                    </Button>
                    <Button @click="goHome"
                        class="flex-1 h-11 rounded-xl text-sm font-medium transition-all duration-200 hover:scale-[1.02] hover:shadow-md active:scale-[0.98]">
                        返回首页
                    </Button>
                </div>
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
.nf-card {
    animation: nf-card-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.nf-code {
    animation: nf-code-in 0.7s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
}

.nf-title {
    animation: nf-slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.25s both;
}

.nf-desc {
    animation: nf-slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.35s both;
}

.nf-actions {
    animation: nf-slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.45s both;
}

@keyframes nf-card-in {
    from {
        opacity: 0;
        transform: translateY(24px) scale(0.95);
    }

    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

@keyframes nf-code-in {
    from {
        opacity: 0;
        transform: scale(0.8);
    }

    to {
        opacity: 1;
        transform: scale(1);
    }
}

@keyframes nf-slide-up {
    from {
        opacity: 0;
        transform: translateY(12px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 网格背景 */
.nf-grid {
    background-image:
        linear-gradient(rgb(0 0 0 / 0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgb(0 0 0 / 0.02) 1px, transparent 1px);
    background-size: 32px 32px;
    mask-image: radial-gradient(ellipse 70% 70% at 50% 50%, black 30%, transparent 100%);
}

:global(.dark) .nf-grid {
    background-image:
        linear-gradient(rgb(255 255 255 / 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgb(255 255 255 / 0.025) 1px, transparent 1px);
}

/* 渐变光晕球 */
.nf-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.12;
    animation: nf-orb-float 14s ease-in-out infinite alternate;
}

.nf-orb-1 {
    width: 380px;
    height: 380px;
    background: #f97316;
    top: -12%;
    left: -5%;
    animation-delay: 0s;
}

.nf-orb-2 {
    width: 320px;
    height: 320px;
    background: #818cf8;
    bottom: -10%;
    right: -5%;
    animation-delay: -5s;
}

.nf-orb-3 {
    width: 220px;
    height: 220px;
    background: #06b6d4;
    top: 60%;
    left: 55%;
    transform: translate(-50%, -50%);
    animation-delay: -9s;
    opacity: 0.06;
}

@keyframes nf-orb-float {
    0% {
        transform: translate(0, 0) scale(1);
    }

    100% {
        transform: translate(-25px, 20px) scale(1.12);
    }
}

/* 暗色模式光晕更柔和 */
:global(.dark) .nf-orb {
    opacity: 0.06;
    filter: blur(100px);
}
</style>
