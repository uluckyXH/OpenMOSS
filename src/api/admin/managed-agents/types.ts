import type { PageResponse } from '../../core/types';

export type ManagedAgentRole = 'planner' | 'executor' | 'reviewer' | 'patrol'
export type ManagedAgentHostPlatform = 'openclaw' | 'codex_cli' | 'claude_code' | 'generic_api_agent'
export type ManagedAgentDeploymentMode = 'create_sub_agent' | 'bind_existing_agent' | 'bind_main_agent'
export type ManagedAgentHostAccessMode = 'local' | 'remote'
export type ManagedAgentStatus = 'draft' | 'configured' | 'deployed' | 'disabled' | 'archived'
export type ManagedAgentHostRenderStrategy = 'host_default' | 'openclaw_workspace_files' | 'openclaw_inline_schedule'
export type ManagedAgentScheduleType = 'interval' | 'cron'
export type ManagedAgentCommProvider = 'feishu' | 'slack' | 'telegram' | 'wechat' | 'email' | 'webhook'
export type ManagedAgentBootstrapPurpose = 'download_script' | 'register_runtime'

export interface HostPlatformCapabilities {
  renderer: boolean
  bootstrap_script: boolean
  skill_bundle: boolean
  prompt_preview: boolean
  schedule: boolean
  comm_binding: boolean
}

export interface HostPlatformMeta {
  key: string
  label: string
  access_modes: string[]
  deployment_modes: string[]
  capabilities: HostPlatformCapabilities
  supported_comm_providers: string[]
}

export interface HostPlatformMetaResponse {
  items: HostPlatformMeta[]
}

export interface ManagedAgentListItem {
  id: string
  name: string
  slug: string
  role: ManagedAgentRole
  description: string
  host_platform: ManagedAgentHostPlatform
  deployment_mode: ManagedAgentDeploymentMode
  host_access_mode: ManagedAgentHostAccessMode
  status: ManagedAgentStatus
  runtime_agent_id: string | null
  config_version: number
  deployed_config_version: number | null
  needs_redeploy: boolean
  online_status: string | null
  data_source: string
  created_at: string
  updated_at: string
}

export type ManagedAgentDetail = ManagedAgentListItem
export type ManagedAgentPageResponse = PageResponse<ManagedAgentListItem>

export interface ManagedAgentListParams {
  page?: number
  page_size?: number
  role?: ManagedAgentRole
  status?: ManagedAgentStatus
}

export interface ManagedAgentCreateInput {
  name: string
  slug: string
  role: ManagedAgentRole
  description?: string
  host_platform?: ManagedAgentHostPlatform
  deployment_mode: ManagedAgentDeploymentMode
  host_access_mode?: ManagedAgentHostAccessMode
  host_agent_identifier?: string
  workdir_path?: string
}

export interface ManagedAgentUpdateInput {
  name?: string
  description?: string
  host_platform?: ManagedAgentHostPlatform
  deployment_mode?: ManagedAgentDeploymentMode
  host_access_mode?: ManagedAgentHostAccessMode
  status?: ManagedAgentStatus
}

export interface ManagedAgentHostConfig {
  id: string
  managed_agent_id: string
  host_platform: string
  host_agent_identifier: string | null
  workdir_path: string | null
  host_config_payload_masked: string | null
  host_metadata_json: string | null
  created_at: string
  updated_at: string
}

export interface ManagedAgentHostConfigInput {
  host_agent_identifier?: string
  workdir_path?: string
  host_config_payload?: string
  host_metadata_json?: string
}

export interface ManagedAgentPromptAsset {
  id: string
  managed_agent_id: string
  template_role: string | null
  system_prompt_content: string
  persona_prompt_content: string
  identity_content: string
  host_render_strategy: ManagedAgentHostRenderStrategy
  authority_source: string
  notes: string | null
  updated_at: string
}

export interface ManagedAgentPromptAssetInput {
  system_prompt_content?: string
  persona_prompt_content?: string
  identity_content?: string
  host_render_strategy?: ManagedAgentHostRenderStrategy
  notes?: string
}

export interface ManagedAgentRenderedArtifact {
  name: string
  content: string
}

export interface ManagedAgentPromptRenderPreview {
  host_platform: string
  host_render_strategy: ManagedAgentHostRenderStrategy
  artifacts: ManagedAgentRenderedArtifact[]
}

export interface ManagedAgentSchedule {
  id: string
  managed_agent_id: string
  name: string
  enabled: boolean
  schedule_type: ManagedAgentScheduleType
  schedule_expr: string
  timeout_seconds: number
  model_override: string | null
  execution_options_json: string | null
  schedule_message_content: string
  created_at: string
  updated_at: string
}

export interface ManagedAgentScheduleCreateInput {
  name: string
  enabled?: boolean
  schedule_type?: ManagedAgentScheduleType
  schedule_expr?: string
  timeout_seconds?: number
  model_override?: string
  execution_options_json?: string
  schedule_message_content?: string
}

export interface ManagedAgentScheduleUpdateInput {
  name?: string
  enabled?: boolean
  schedule_type?: ManagedAgentScheduleType
  schedule_expr?: string
  timeout_seconds?: number
  model_override?: string
  execution_options_json?: string
  schedule_message_content?: string
}

export interface ManagedAgentCommBinding {
  id: string
  managed_agent_id: string
  provider: ManagedAgentCommProvider
  binding_key: string
  display_name: string | null
  enabled: boolean
  routing_policy_json: string | null
  metadata_json: string | null
  config_payload_masked: string | null
  created_at: string
  updated_at: string
}

export interface ManagedAgentCommBindingCreateInput {
  provider: ManagedAgentCommProvider
  binding_key: string
  display_name?: string
  enabled?: boolean
  routing_policy_json?: string
  metadata_json?: string
  config_payload?: string
}

export interface ManagedAgentCommBindingUpdateInput {
  provider?: ManagedAgentCommProvider
  binding_key?: string
  display_name?: string
  enabled?: boolean
  routing_policy_json?: string
  metadata_json?: string
  config_payload?: string
}

export interface ManagedAgentBootstrapTokenCreateInput {
  purpose: ManagedAgentBootstrapPurpose
  ttl_seconds: number
  scope_json?: string
}

export interface ManagedAgentBootstrapTokenCreateResponse {
  id: string
  managed_agent_id: string
  token: string
  purpose: ManagedAgentBootstrapPurpose
  scope_json: string | null
  expires_at: string
  created_at: string
}

export interface ManagedAgentBootstrapTokenListItem {
  id: string
  managed_agent_id: string
  token_masked: string
  purpose: ManagedAgentBootstrapPurpose
  scope_json: string | null
  expires_at: string
  used_at: string | null
  revoked_at: string | null
  created_at: string
  is_valid: boolean
}

export interface ManagedAgentBootstrapScriptParams {
  selected_artifacts?: string[]
  include_schedule?: boolean
  include_comm_bindings?: boolean
  register_ttl_seconds?: number
  bundle_ttl_seconds?: number
}

export interface ManagedAgentBootstrapScriptResponse {
  script: string
  register_token_id: string
  register_token_expires_at: string
}

export interface ManagedAgentOnboardingMessageParams {
  selected_artifacts?: string[]
  include_schedule?: boolean
  include_comm_bindings?: boolean
  download_ttl_seconds?: number
}

export interface ManagedAgentOnboardingMessageResponse {
  message: string
  curl_command: string
  download_token_id: string
  download_token_expires_at: string
}
