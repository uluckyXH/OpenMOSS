import api from '../core/http';

export interface PromptTemplate {
  role: string
  filename: string
  content: string
}

export interface AgentPromptMeta {
  slug: string
  filename: string
  name: string
  role: string
  description: string
  created_at: string
  example: boolean
  has_frontmatter: boolean
  status: 'ok' | 'rename_suggested' | 'unconfigured'
}

export interface AgentPromptDetail extends AgentPromptMeta {
  content: string
}

export const promptsApi = {
  listTemplates: () => api.get<PromptTemplate[]>('/admin/prompts/templates'),
  getTemplate: (role: string) => api.get<PromptTemplate>(`/admin/prompts/templates/${role}`),
  updateTemplate: (role: string, content: string) => api.put(`/admin/prompts/templates/${role}`, { content }),
  listAgents: () => api.get<AgentPromptMeta[]>('/admin/prompts/agents'),
  getAgent: (slug: string) => api.get<AgentPromptDetail>(`/admin/prompts/agents/${slug}`),
  createAgent: (data: {
    slug: string
    name: string
    role: string
    description?: string
    content: string
  }) => api.post('/admin/prompts/agents', data),
  updateAgent: (slug: string, data: {
    name?: string
    role?: string
    description?: string
    content?: string
  }) => api.put(`/admin/prompts/agents/${slug}`, data),
  deleteAgent: (slug: string) => api.delete(`/admin/prompts/agents/${slug}`),
  compose: (slug: string) => api.get<{ slug: string; prompt: string }>(`/admin/prompts/compose/${slug}`),
  getOnboarding: (role: string) => api.get<{ role: string; content: string }>(`/admin/prompts/onboarding/${role}`),
};
