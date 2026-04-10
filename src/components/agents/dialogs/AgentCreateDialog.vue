<script setup lang="ts">
import { ref } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentApi,
  type ManagedAgentCreateInput,
  type ManagedAgentHostPlatform,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ChevronDown, Loader2 } from 'lucide-vue-next';
import { usePlatformMeta } from '@/composables/agents/usePlatformMeta';


const open = defineModel<boolean>('open', { default: false });
const emit = defineEmits<{ created: [] }>();

const { platformOptions, deployModeOptionsFor, accessModeOptionsFor, loadPlatforms } = usePlatformMeta();
void loadPlatforms();

const creatingAgent = ref(false);
const createError = ref('');
const createForm = ref<ManagedAgentCreateInput>({
  name: '', slug: '', role: 'executor', description: '',
  host_platform: 'openclaw', deployment_mode: 'create_sub_agent',
  host_access_mode: 'local', host_agent_identifier: '', workdir_path: '',
});

const roleOptions: { value: string; label: string }[] = [
  { value: 'planner', label: '规划者' },
  { value: 'executor', label: '执行者' },
  { value: 'reviewer', label: '审查者' },
  { value: 'patrol', label: '巡查者' },
];

function resetForm() {
  createForm.value = {
    name: '', slug: '', role: 'executor', description: '',
    host_platform: 'openclaw', deployment_mode: 'create_sub_agent',
    host_access_mode: 'local', host_agent_identifier: '', workdir_path: '',
  };
  createError.value = '';
}

async function handleCreate() {
  const form = createForm.value;
  if (!form.name.trim()) { createError.value = '名称不能为空'; return; }
  if (!form.slug.trim()) { createError.value = 'Slug 不能为空'; return; }
  creatingAgent.value = true;
  createError.value = '';
  try {
    await managedAgentApi.create({
      ...form,
      name: form.name.trim(),
      slug: form.slug.trim(),
      description: form.description?.trim() || undefined,
      host_agent_identifier: form.host_agent_identifier?.trim() || undefined,
      workdir_path: form.workdir_path?.trim() || undefined,
    });
    toast.success(`Agent「${form.name.trim()}」创建成功`);
    open.value = false;
    resetForm();
    emit('created');
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    createError.value = msg ?? '创建失败，请稍后再试';
  } finally {
    creatingAgent.value = false;
  }
}

function close() {
  open.value = false;
  resetForm();
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close" />
      <div
        class="relative z-10 w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <h2 class="text-lg font-semibold mb-5">新建 Agent</h2>

        <!-- 基本信息 -->
        <div class="space-y-3 mb-6">
          <div class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">基本信息</div>
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">名称 <span class="text-rose-500">*</span></label>
            <Input v-model="createForm.name" placeholder="如：AI小灰" />
          </div>
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">Slug <span class="text-rose-500">*</span></label>
            <Input v-model="createForm.slug" placeholder="如：ai-xiaohui（稳定标识）" class="font-mono" />
          </div>
          <div>
            <label class="text-xs text-muted-foreground mb-1.5 block">角色 <span class="text-rose-500">*</span></label>
            <div class="grid grid-cols-2 gap-1.5">
              <label v-for="opt in roleOptions" :key="opt.value"
                class="flex items-center gap-2 cursor-pointer rounded-lg border px-3 py-2 transition-colors"
                :class="createForm.role === opt.value ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/30'">
                <input type="radio" :value="opt.value" v-model="createForm.role" class="accent-primary" />
                <span class="text-sm">{{ opt.label }}</span>
              </label>
            </div>
          </div>
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">描述</label>
            <textarea v-model="createForm.description" rows="2"
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              placeholder="可选描述" />
          </div>
        </div>

        <!-- 部署配置 -->
        <div class="space-y-3 mb-5">
          <div class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">部署配置</div>
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">Agent 平台</label>
            <DropdownMenu v-if="platformOptions.length > 0">
              <DropdownMenuTrigger as-child>
                <Button variant="outline" size="sm" class="h-9 w-full justify-between text-sm font-normal">
                  {{platformOptions.find(o => o.value === createForm.host_platform)?.label ?? createForm.host_platform
                  }}
                  <ChevronDown class="h-3.5 w-3.5 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" class="min-w-[200px]">
                <DropdownMenuRadioGroup :model-value="createForm.host_platform"
                  @update:model-value="(v) => createForm.host_platform = String(v) as ManagedAgentHostPlatform">
                  <DropdownMenuRadioItem v-for="option in platformOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>
            <Input v-else v-model="createForm.host_platform" placeholder="openclaw" />
          </div>
          <div>
            <label class="text-xs text-muted-foreground mb-1.5 block">部署模式 <span class="text-rose-500">*</span></label>
            <div class="space-y-1.5">
              <label v-for="option in deployModeOptionsFor(createForm.host_platform ?? 'openclaw')" :key="option.value"
                class="flex items-center gap-2 cursor-pointer rounded-lg border px-3 py-2 transition-colors"
                :class="createForm.deployment_mode === option.value ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/30'">
                <input type="radio" :value="option.value" v-model="createForm.deployment_mode" class="accent-primary" />
                <span class="text-sm">{{ option.label }}</span>
              </label>
            </div>
          </div>
          <div>
            <label class="text-xs text-muted-foreground mb-1.5 block">平台归属</label>
            <div class="space-y-1.5">
              <label v-for="option in accessModeOptionsFor(createForm.host_platform ?? 'openclaw')" :key="option.value"
                class="flex items-start gap-2.5 cursor-pointer rounded-lg border px-3 py-2.5 transition-colors"
                :class="createForm.host_access_mode === option.value ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/30'">
                <input type="radio" :value="option.value" v-model="createForm.host_access_mode"
                  class="accent-primary mt-0.5" />
                <div class="space-y-0.5">
                  <div class="text-sm flex items-center gap-1.5">
                    {{ option.label }}
                    <Badge v-if="option.value === 'remote'" variant="outline"
                      class="text-[9px] px-1 py-0 text-amber-600 border-amber-300">Beta</Badge>
                  </div>
                  <div class="text-[11px] text-muted-foreground leading-tight">
                    {{ option.value === 'local'
                      ? '属于当前 OpenMOSS 默认对接的 OpenClaw 平台环境，默认共享该平台的公共工作目录和平台侧配置。'
                      : '属于另一套独立的 OpenClaw 平台环境，不默认共享当前主力平台的公共工作目录，需要按外部平台方式接入。' }}
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>

        <!-- 错误提示 -->
        <p v-if="createError" class="text-xs text-rose-500 mb-3">{{ createError }}</p>

        <!-- 按钮 -->
        <div class="flex gap-3">
          <Button variant="outline" class="flex-1" :disabled="creatingAgent" @click="close">取消</Button>
          <Button class="flex-1" :disabled="creatingAgent" @click="handleCreate">
            <Loader2 v-if="creatingAgent" class="h-4 w-4 animate-spin mr-1" />
            创建
          </Button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
