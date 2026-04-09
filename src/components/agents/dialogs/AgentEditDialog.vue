<script setup lang="ts">
import { ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { managedAgentApi, type ManagedAgentListItem, type ManagedAgentStatus } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2 } from 'lucide-vue-next';

const open = defineModel<boolean>('open', { default: false });
const props = defineProps<{ agent: ManagedAgentListItem | null }>();
const emit = defineEmits<{ saved: [] }>();

const editForm = ref({ name: '', description: '', status: '' as ManagedAgentStatus });
const savingEdit = ref(false);
const editError = ref('');

watch(() => open.value, (val) => {
  if (val && props.agent) {
    editForm.value = {
      name: props.agent.name,
      description: props.agent.description ?? '',
      status: props.agent.status,
    };
    editError.value = '';
  }
});

async function handleSave() {
  if (!props.agent) return;
  const name = editForm.value.name.trim();
  if (!name) { editError.value = '名称不能为空'; return; }
  savingEdit.value = true;
  editError.value = '';
  try {
    await managedAgentApi.update(props.agent.id, {
      name,
      description: editForm.value.description.trim() || undefined,
      status: editForm.value.status,
    });
    toast.success('更新成功');
    open.value = false;
    emit('saved');
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    editError.value = msg ?? '保存失败';
  } finally {
    savingEdit.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="open = false" />
      <div
        class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <h2 class="text-lg font-semibold mb-4">编辑 Agent</h2>
        <div class="space-y-3 mb-4">
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">名称</label>
            <Input v-model="editForm.name" />
          </div>
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">描述</label>
            <textarea v-model="editForm.description" rows="3"
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none" />
          </div>
        </div>
        <p v-if="editError" class="text-xs text-rose-500 mb-3">{{ editError }}</p>
        <div class="flex gap-3">
          <Button variant="outline" class="flex-1" :disabled="savingEdit" @click="open = false">取消</Button>
          <Button class="flex-1" :disabled="savingEdit" @click="handleSave">
            <Loader2 v-if="savingEdit" class="h-4 w-4 animate-spin mr-1" />
            保存
          </Button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
