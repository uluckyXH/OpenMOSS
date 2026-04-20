<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { Play, Github } from 'lucide-vue-next';

const emit = defineEmits<{
  startDemo: []
}>();

// Typewriter
const phrases = [
  'OpenMOSS——一个多Agent协同、自组织自修复自进化的AI公司操作系统，现已开源。',
  '4 种角色各司其职，全程零人工编排，7×24 无人值守。',
  '提交 → 审查 → 返工 → 再审，闭环质控保障每一份交付物。',
];

const displayText = ref('');
const prefix = '';
let timer: ReturnType<typeof setTimeout> | null = null;
let phraseIdx = 0;
let charIdx = 0;
let isDeleting = false;

function tick() {
  const current = phrases[phraseIdx]!;

  if (!isDeleting) {
    // typing
    charIdx++;
    displayText.value = current.slice(0, charIdx);
    if (charIdx >= current.length) {
      // pause then delete
      timer = setTimeout(() => { isDeleting = true; tick(); }, 2000);
      return;
    }
    timer = setTimeout(tick, 60);
  } else {
    // deleting
    charIdx--;
    displayText.value = current.slice(0, charIdx);
    if (charIdx <= 0) {
      isDeleting = false;
      phraseIdx = (phraseIdx + 1) % phrases.length;
      timer = setTimeout(tick, 400);
      return;
    }
    timer = setTimeout(tick, 30);
  }
}

onMounted(() => {
  timer = setTimeout(tick, 800);
});

onUnmounted(() => {
  if (timer) clearTimeout(timer);
});
</script>

<template>
  <section class="hero">
    <h1>3分钟，体验<em>AI公司</em><br>的高效率</h1>
    <p class="hero-sub">
      {{ prefix }}<span class="typed">{{ displayText }}</span><span class="cursor">|</span>
    </p>
    <div class="hero-actions">
      <button class="btn-hero btn-hero-dark" @click="emit('startDemo')">
        <Play :size="15" :stroke-width="2.5" fill="currentColor" />
        开始体验 Demo
      </button>
      <a class="btn-hero btn-hero-outline" href="https://github.com/uluckyXH/OpenMOSS" target="_blank">
        <Github :size="15" :stroke-width="2" />
        GitHub
      </a>
      <span class="hero-note">无需安装 · 直接在浏览器中体验</span>
    </div>
  </section>
</template>

<style scoped>
.hero {
  max-width: 860px;
  margin: 0 auto;
  padding: 64px 40px 48px;
  position: relative;
  z-index: 1;
  text-align: center;
}

.page-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F5F4F0;
  border: 1px solid #E8E6E0;
  border-radius: 14px;
  color: #8B6F4E;
  animation: fadeUp 0.5s ease both;
  overflow: hidden;
}

.hero-logo {
  width: 56px;
  height: 56px;
  object-fit: contain;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #FBF3DC;
  border: 1px solid #E8D89A;
  color: #7A6020;
  padding: 3px 12px;
  border-radius: 4px;
  font-size: 12.5px;
  font-weight: 500;
  margin-bottom: 20px;
  font-family: 'IBM Plex Mono', monospace;
  animation: fadeUp 0.5s 0.05s ease both;
}

h1 {
  font-family: 'Lora', serif;
  font-size: clamp(36px, 5.5vw, 60px);
  font-weight: 700;
  line-height: 1.12;
  letter-spacing: -1px;
  margin: 0 0 24px;
  color: #1A1917;
  animation: fadeUp 0.5s 0.1s ease both;
}

h1 em {
  font-style: italic;
  color: #8B6F4E;
}

.hero-sub {
  font-size: 17px;
  color: #4A4845;
  max-width: 560px;
  line-height: 1.75;
  margin: 0 auto 32px;
  animation: fadeUp 0.5s 0.15s ease both;
  min-height: 3.6em;
}

.typed {
  color: #1A1917;
}

.cursor {
  color: #8B6F4E;
  font-weight: 300;
  animation: blink 1s step-end infinite;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
  animation: fadeUp 0.5s 0.2s ease both;
}

.btn-hero {
  padding: 10px 22px;
  border-radius: 7px;
  font-size: 14.5px;
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.btn-hero-dark {
  background: #1A1917;
  color: #FAFAF8;
  border: none;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15), 0 4px 12px rgba(0, 0, 0, 0.1);
}

.btn-hero-dark:hover {
  background: #2e2b27;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2), 0 6px 20px rgba(0, 0, 0, 0.12);
  transform: translateY(-1px);
}

.btn-hero-outline {
  background: #FFFFFF;
  color: #4A4845;
  border: 1px solid #D4D0C8;
}

.btn-hero-outline:hover {
  border-color: #4A4845;
  color: #1A1917;
}

.hero-note {
  font-size: 13px;
  color: #8C8A84;
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  justify-content: center;
  margin-top: 4px;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

@media (max-width: 640px) {
  .hero {
    padding: 40px 20px 32px;
  }

  .hero-sub {
    font-size: 15px;
  }
}
</style>
