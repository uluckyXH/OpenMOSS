<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { managedAgentApi, type ManagedAgentListItem } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, Trash2 } from 'lucide-vue-next';

const open = defineModel<boolean>('open', { default: false });
const props = defineProps<{ agent: ManagedAgentListItem | null }>();
const emit = defineEmits<{ deleted: [] }>();

const deleteConfirmInput = ref('');
const deletingAgent = ref(false);
const deleteError = ref('');

const deleteConfirmValid = computed(() =>
  props.agent ? deleteConfirmInput.value.trim() === `确认删除${props.agent.name}` : false
);

watch(() => open.value, (val) => {
  if (val) {
    deleteConfirmInput.value = '';
    deleteError.value = '';
  }
});

async function handleDelete() {
  if (!props.agent || !deleteConfirmValid.value) return;
  deletingAgent.value = true;
  deleteError.value = '';
  try {
    await managedAgentApi.remove(props.agent.id);
    toast.success('已删除');
    open.value = false;
    emit('deleted');
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    deleteError.value = msg ?? '删除失败';
  } finally {
    deletingAgent.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="open = false" />
      <div
        class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div class="text-center space-y-2 mb-4">
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-100">
            <Trash2 class="h-5 w-5 text-rose-600" />
          </div>
          <h2 class="text-lg font-semibold">删除 Agent</h2>
          <p class="text-sm text-muted-foreground">
            即将删除 <span class="font-medium text-foreground">{{ agent?.name }}</span>，
            将同时清除所有关联子资源（平台配置、Prompt、定时任务、通讯渠道、Bootstrap Token）。
          </p>
        </div>
        <div class="mb-4">
          <label class="text-xs text-muted-foreground mb-1 block">
            输入 <span class="font-mono font-medium text-foreground">确认删除{{ agent?.name }}</span> 以确认
          </label>
          <Input v-model="deleteConfirmInput" placeholder="请输入确认文字" />
        </div>
        <p v-if="deleteError" class="text-xs text-rose-500 mb-3">{{ deleteError }}</p>
        <div class="flex gap-3">
          <Button variant="outline" class="flex-1" :disabled="deletingAgent" @click="open = false">取消</Button>
          <Button variant="destructive" class="flex-1" :disabled="!deleteConfirmValid || deletingAgent"
            @click="handleDelete">
            <Loader2 v-if="deletingAgent" class="h-4 w-4 animate-spin mr-1" />
            确认删除
          </Button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
