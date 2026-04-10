<script setup lang="ts">
import { computed } from 'vue';
import type { HostConfigFieldMeta } from '@/api/client';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { ChevronDown, ShieldAlert } from 'lucide-vue-next';

const props = defineProps<{
  field: HostConfigFieldMeta;
  modelValue: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const value = computed({
  get() { return props.modelValue ?? ''; },
  set(v: string) { emit('update:modelValue', v); },
});

const selectedOptionLabel = computed(() => {
  if (props.field.type !== 'select' || !props.field.options) return '';
  return props.field.options.find(o => o.value === value.value)?.label ?? value.value;
});
</script>

<template>
  <div class="space-y-1.5">
    <!-- 标签行 -->
    <label class="text-xs text-muted-foreground flex items-center gap-1.5">
      {{ field.label }}
      <span v-if="field.required" class="text-rose-500">*</span>
      <span v-if="field.sensitive"
        class="inline-flex items-center gap-0.5 text-[9px] px-1 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20">
        <ShieldAlert class="h-2.5 w-2.5" />敏感
      </span>
    </label>

    <!-- text -->
    <Input v-if="field.type === 'text'"
      v-model="value"
      :placeholder="field.placeholder"
      :disabled="disabled"
      class="font-mono text-sm" />

    <!-- password -->
    <Input v-else-if="field.type === 'password'"
      v-model="value"
      type="password"
      :placeholder="field.placeholder"
      :disabled="disabled"
      class="font-mono text-sm" />

    <!-- textarea -->
    <textarea v-else-if="field.type === 'textarea'"
      v-model="value"
      rows="3"
      :placeholder="field.placeholder"
      :disabled="disabled"
      class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none disabled:opacity-50" />

    <!-- json -->
    <textarea v-else-if="field.type === 'json'"
      v-model="value"
      rows="3"
      :placeholder="field.placeholder ?? '{ }'"
      :disabled="disabled"
      class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none disabled:opacity-50" />

    <!-- select -->
    <DropdownMenu v-else-if="field.type === 'select' && field.options">
      <DropdownMenuTrigger as-child>
        <Button variant="outline" size="sm"
          class="h-8 w-full justify-between text-xs font-normal"
          :disabled="disabled">
          {{ selectedOptionLabel || field.placeholder || '请选择' }}
          <ChevronDown class="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" class="min-w-[200px]">
        <DropdownMenuRadioGroup :model-value="value"
          @update:model-value="(v) => value = String(v)">
          <DropdownMenuRadioItem v-for="opt in field.options" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>

    <!-- fallback -->
    <Input v-else
      v-model="value"
      :placeholder="field.placeholder"
      :disabled="disabled"
      class="font-mono text-sm" />

    <!-- 字段说明 -->
    <p v-if="field.description" class="text-[11px] text-muted-foreground/50 leading-relaxed">
      {{ field.description }}
    </p>
    <p v-if="field.sensitive" class="text-[11px] text-muted-foreground/40">
      留空表示不修改现有值。
    </p>
  </div>
</template>
