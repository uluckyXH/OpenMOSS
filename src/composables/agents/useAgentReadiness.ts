import { computed, type Ref } from 'vue';
import type { ManagedAgentListItem, ManagedAgentReadiness } from '@/api/client';

export interface TabReadiness {
  /** 基础信息 — 始终就绪（创建时已填写） */
  basic: boolean;
  /** 平台配置 — 后端 readiness.host_config */
  host: boolean;
  /** Prompt — 后端 readiness.prompt_asset（选填） */
  prompt: boolean;
  /** 定时任务 — 前置：host 就绪 */
  schedule: boolean;
  /** 通讯渠道 — 前置：host 就绪 */
  comm: boolean;
  /** 部署接入 — 前置：host 就绪 */
  bootstrap: boolean;
}

const EMPTY_READINESS: TabReadiness = {
  basic: true, host: false, prompt: false,
  schedule: false, comm: false, bootstrap: false,
};

/**
 * 从后端返回的 agent.readiness 字段派生各 Tab 的可用状态。
 *
 * 改造前：前端并行探测 host_config + prompt_asset（N+1 问题、逻辑分裂）
 * 改造后：直接消费后端嵌入的 readiness 对象，零额外请求。
 */
export function useAgentReadiness(agent: Ref<ManagedAgentListItem | null>) {
  const readiness = computed<TabReadiness>(() => {
    const r = agent.value?.readiness;
    if (!r) return EMPTY_READINESS;

    return {
      basic: true,
      host: r.host_config,
      prompt: r.prompt_asset,
      schedule: r.host_config,  // 前置：host 就绪
      comm: r.host_config,      // 前置：host 就绪
      bootstrap: r.host_config, // 前置：host 就绪（部署脚本仅需平台配置）
    };
  });

  /** 必填项完成数 / 总必填数 */
  const progress = computed(() => {
    const required = [true, readiness.value.host];
    return { done: required.filter(Boolean).length, total: required.length };
  });

  /** 后端原始 readiness（用于卡片展示 count 等） */
  const raw = computed<ManagedAgentReadiness | null>(() => agent.value?.readiness ?? null);

  return { readiness, progress, raw };
}
