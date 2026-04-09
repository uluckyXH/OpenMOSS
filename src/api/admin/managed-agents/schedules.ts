import api from '../../core/http';
import type { ManagedAgentSchedule, ManagedAgentScheduleCreateInput, ManagedAgentScheduleUpdateInput } from './types';

export const managedAgentScheduleApi = {
  list: (agentId: string) => api.get<ManagedAgentSchedule[]>(`/admin/managed-agents/${agentId}/schedules`),
  create: (agentId: string, data: ManagedAgentScheduleCreateInput) =>
    api.post<ManagedAgentSchedule>(`/admin/managed-agents/${agentId}/schedules`, data),
  update: (agentId: string, scheduleId: string, data: ManagedAgentScheduleUpdateInput) =>
    api.put<ManagedAgentSchedule>(`/admin/managed-agents/${agentId}/schedules/${scheduleId}`, data),
  remove: (agentId: string, scheduleId: string) =>
    api.delete(`/admin/managed-agents/${agentId}/schedules/${scheduleId}`),
};
