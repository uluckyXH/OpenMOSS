import { computed, onMounted, ref, watch } from 'vue';
import {
  managedAgentHostConfigApi,
  managedAgentPromptAssetApi,
} from '@/api/client';

export interface TabReadiness {
  /** 基础信息 — 始终就绪（创建时已填写） */
  basic: boolean;
  /** 平台配置 — host_config 存在且有实质内容 */
  host: boolean;
  /** Prompt — prompt_asset 存在且 system_prompt 非空 */
  prompt: boolean;
  /** 定时任务 — 前置：prompt 就绪 */
  schedule: boolean;
  /** 通讯渠道 — 前置：prompt 就绪 */
  comm: boolean;
  /** 部署接入 — 前置：host + prompt 就绪 */
  bootstrap: boolean;
}

/**
 * 根据 agentId 并行探测各子资源存在性，计算 Tab 可用状态。
 * Tab 始终可浏览，但未就绪的 Tab 内编辑操作应禁用。
 */
export function useAgentReadiness(agentId: () => string) {
  const hostReady = ref(false);
  const promptReady = ref(false);
  const loading = ref(false);

  async function probe() {
    loading.value = true;
    const id = agentId();

    // 并行探测，用 catch 捕获 404 = 未配置
    const [hostResult, promptResult] = await Promise.allSettled([
      managedAgentHostConfigApi.get(id),
      managedAgentPromptAssetApi.get(id),
    ]);

    // host_config 存在即视为就绪（创建 Agent 时自动初始化）
    if (hostResult.status === 'fulfilled') {
      const cfg = hostResult.value.data;
      // 有 host_agent_identifier 或 workdir_path 才算"有实质内容"
      hostReady.value = !!(cfg.host_agent_identifier || cfg.workdir_path);
    } else {
      hostReady.value = false;
    }

    // prompt_asset 存在且 system_prompt 非空
    if (promptResult.status === 'fulfilled') {
      const pa = promptResult.value.data;
      promptReady.value = !!(pa.system_prompt_content?.trim());
    } else {
      promptReady.value = false;
    }

    loading.value = false;
  }

  onMounted(() => { void probe(); });
  watch(agentId, () => { void probe(); });

  const readiness = computed<TabReadiness>(() => ({
    basic: true,
    host: hostReady.value,
    prompt: promptReady.value,
    schedule: promptReady.value,
    comm: promptReady.value,
    bootstrap: hostReady.value && promptReady.value,
  }));

  /** 完成数 / 总必填数 */
  const progress = computed(() => {
    const required = [readiness.value.basic, readiness.value.host, readiness.value.prompt];
    return { done: required.filter(Boolean).length, total: required.length };
  });

  return { readiness, progress, loading, refresh: probe };
}
