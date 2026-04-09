// useAgentFormatters — 格式化函数集合

export function formatRole(role: string) {
  return { planner: '规划者', executor: '执行者', reviewer: '审查者', patrol: '巡查者' }[role] ?? role;
}

export function getRoleBadgeClass(role: string) {
  return {
    planner: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
    executor: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    reviewer: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    patrol: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  }[role] ?? 'bg-muted text-muted-foreground';
}

export function getRoleBarClass(role: string) {
  return {
    planner: 'bg-violet-500',
    executor: 'bg-sky-500',
    reviewer: 'bg-amber-500',
    patrol: 'bg-emerald-500',
  }[role] ?? 'bg-muted';
}

export function formatStatus(status: string) {
  return {
    draft: '草稿', configured: '已配置', deployed: '已部署',
    disabled: '已禁用', archived: '已归档',
  }[status] ?? status;
}

export function getStatusDotClass(status: string) {
  return {
    draft: 'bg-zinc-400', configured: 'bg-blue-400', deployed: 'bg-emerald-400',
    disabled: 'bg-amber-400', archived: 'bg-zinc-600',
  }[status] ?? 'bg-zinc-400';
}

export function getStatusBadgeClass(status: string) {
  return {
    draft: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
    configured: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    deployed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    disabled: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    archived: 'bg-zinc-700/10 text-zinc-500 border-zinc-700/20',
  }[status] ?? 'bg-muted text-muted-foreground';
}

export function formatDeployMode(mode: string) {
  return {
    create_sub_agent: '创建子 Agent',
    bind_existing_agent: '绑定现有 Agent',
    bind_main_agent: '绑定主 Agent',
  }[mode] ?? mode;
}

export function formatDate(value: string | null) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return value; }
}

export const deployModeLabels: Record<string, string> = {
  create_sub_agent: '创建子 Agent',
  bind_existing_agent: '绑定现有 Agent',
  bind_main_agent: '绑定主 Agent',
};

export const accessModeLabels: Record<string, string> = {
  local: '主力 OpenClaw',
  remote: '外部 OpenClaw',
};
