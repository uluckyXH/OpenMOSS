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
export type ManagedAgentDeployScriptIntent = 'bootstrap' | 'sync'
export type ManagedAgentDeploymentResourceType = 'prompt' | 'schedule' | 'comm_binding'
export type ManagedAgentDeploymentChangeType = 'add' | 'update' | 'remove'
export type ManagedAgentDeploymentSnapshotStatus = 'pending' | 'confirmed' | 'failed' | 'timeout' | 'cancelled'

export interface HostPlatformCapabilities {
  renderer: boolean
  bootstrap_script: boolean
  skill_bundle: boolean
  prompt_preview: boolean
  schedule: boolean
  comm_binding: boolean
}

export type HostConfigFieldType = 'text' | 'textarea' | 'password' | 'json' | 'select'

export interface HostConfigFieldMeta {
  key: string
  label: string
  type: HostConfigFieldType
  placeholder?: string
  description?: string
  required?: boolean
  options?: Array<{ value: string; label: string }>
  sensitive?: boolean
  group?: string
}

export interface HostConfigUIHints {
  description: string
  fields: HostConfigFieldMeta[]
}

export interface PromptRenderStrategyMeta {
  value: ManagedAgentHostRenderStrategy | string
  label: string
  description: string
  /** 是否为该平台的默认策略 */
  is_default?: boolean
}

export interface PromptSectionMeta {
  key: 'system_prompt_content' | 'persona_prompt_content' | 'identity_content' | string
  label: string
  placeholder?: string
  required: boolean
  /** 简短一句话描述（始终可见） */
  description?: string
  /** 完整详细说明（点击 ? 展开） */
  detail?: string
}

export interface PromptUIHints {
  description: string
  render_strategies: PromptRenderStrategyMeta[]
  sections: PromptSectionMeta[]
}

export interface ScheduleUIHints {
  description?: string
  supported_types?: ManagedAgentScheduleType[]
  default_expr?: string
  default_timeout?: number
}

export interface CommUIHints {
  description?: string
}

export type CommProviderFieldType = 'text' | 'password' | 'switch'

export interface CommProviderSchemaField {
  key: string
  label: string
  type: CommProviderFieldType
  required: boolean
  advanced?: boolean | null
  placeholder?: string | null
  description?: string | null
  sensitive?: boolean | null
  default?: string | boolean | number | null
}

export interface CommProviderSchema {
  provider: ManagedAgentCommProvider
  label: string
  description: string
  supports_multiple_bindings: boolean
  fields: CommProviderSchemaField[]
}

export interface CommProviderValidateResponse {
  valid: boolean
  errors: string[]
}

export interface BootstrapUIHints {
  description?: string
  deploy_guide?: string
  onboarding_guide?: string
}

export interface PlatformUIHints {
  host_config: HostConfigUIHints
  prompt: PromptUIHints
  schedule?: ScheduleUIHints
  comm?: CommUIHints
  bootstrap?: BootstrapUIHints
}

export interface HostPlatformMeta {
  key: string
  label: string
  description: string
  access_modes: string[]
  deployment_modes: string[]
  capabilities: HostPlatformCapabilities
  supported_comm_providers: string[]
  ui_hints: PlatformUIHints
}

export interface HostPlatformMetaResponse {
  items: HostPlatformMeta[]
}

/** Agent 配置就绪度（由后端计算，嵌入在列表/详情返回值中） */
export interface ManagedAgentReadiness {
  /** 平台配置是否就绪 */
  host_config: boolean
  /** Prompt 资产是否就绪 */
  prompt_asset: boolean
  /** 定时任务数量 */
  schedules_count: number
  /** 通讯渠道数量 */
  comm_bindings_count: number
  /** 是否满足部署条件（host_config + prompt_asset 都 ready） */
  deploy_ready: boolean
}

/** 运行态身份摘要（完整 API Key 不会在详情接口回显） */
export interface ManagedAgentRuntimeIdentity {
  /** 是否已完成运行态注册 */
  registered: boolean
  /** 关联的运行态 Agent ID */
  runtime_agent_id: string | null
  /** 脱敏后的运行态 API Key */
  api_key_masked: string | null
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
  readiness: ManagedAgentReadiness
  runtime_identity: ManagedAgentRuntimeIdentity
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

export interface ManagedAgentRuntimeApiKeyResetResponse {
  runtime_agent_id: string
  api_key: string
  api_key_masked: string
  message: string
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
  schedule_type: ManagedAgentScheduleType
  schedule_expr: string
  timeout_seconds: number
  model_override?: string
  execution_options_json?: string
  /** 定时唤醒提示词，必填且不能为空白 */
  schedule_message_content: string
}

export interface ManagedAgentScheduleUpdateInput {
  name?: string
  enabled?: boolean
  schedule_type?: ManagedAgentScheduleType
  schedule_expr?: string
  timeout_seconds?: number
  model_override?: string
  execution_options_json?: string
  /** 更新后不能为空白 */
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

export interface FeishuCommBinding {
  id: string
  provider: 'feishu'
  account_id: string
  account_name: string | null
  enabled: boolean
  app_id_masked: string
  app_secret_masked: string
  created_at: string
  updated_at: string
}

export interface FeishuCommBindingCreateInput {
  account_id: string
  app_id: string
  app_secret: string
  account_name?: string | null
  enabled?: boolean
}

export interface FeishuCommBindingUpdateInput {
  app_id?: string
  app_secret?: string
  account_name?: string | null
  enabled?: boolean
}

export interface FeishuCommBindingValidateInput {
  account_id?: string
  app_id?: string
  app_secret?: string
  account_name?: string | null
  enabled?: boolean
}

export interface FeishuCommSuggestResponse {
  account_id: string | null
  host_agent_identifier: string | null
  message: string | null
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

export interface ManagedAgentDeploySelectionInput {
  script_intent: ManagedAgentDeployScriptIntent
  prompt_artifact_keys?: string[]
  schedule_ids?: string[]
  comm_binding_ids?: string[]
}

export interface ManagedAgentDeployScriptInput extends ManagedAgentDeploySelectionInput {
  register_ttl_seconds?: number
  download_ttl_seconds?: number
  /** 部署快照超时时间（秒），默认 1800，最小 60，最大 86400 */
  snapshot_timeout_seconds?: number
  /** 是否确认替换同 Agent + 同 script_intent 的旧 pending 快照，默认 false */
  replace_pending_snapshot?: boolean
}

export interface ManagedAgentDeployScriptConflictSnapshot {
  id: string
  script_intent: ManagedAgentDeployScriptIntent
  created_at: string
  expires_at: string | null
  is_likely_timeout: boolean
}

export interface ManagedAgentDeployScriptConflictDetail {
  error_code: 'DEPLOYMENT_SNAPSHOT_CONFLICT'
  message: string
  conflict_snapshot: ManagedAgentDeployScriptConflictSnapshot
}

export interface ManagedAgentDeployChangesetItem {
  resource_type: ManagedAgentDeploymentResourceType
  change_type: ManagedAgentDeploymentChangeType
  resource_id: string | null
  resource_key: string | null
  label: string
  enabled?: boolean | null
}

export interface ManagedAgentDeployChangeset {
  items: ManagedAgentDeployChangesetItem[]
  validation_errors: string[]
  is_valid: boolean
}

export interface ManagedAgentDeployPreviewResponse {
  script_intent: ManagedAgentDeployScriptIntent
  changeset: ManagedAgentDeployChangeset
  has_removals: boolean
}

export interface ManagedAgentDeployScriptResponse {
  snapshot_id: string
  status: 'pending'
  config_version: number
  changeset: ManagedAgentDeployChangeset
}

export interface ManagedAgentDeploymentSnapshot {
  id: string
  managed_agent_id: string
  script_intent: ManagedAgentDeployScriptIntent
  config_version: number
  snapshot_json: string
  status: ManagedAgentDeploymentSnapshotStatus
  failure_detail_json: string | null
  created_at: string
  /** 超时截止时间，创建快照时根据 snapshot_timeout_seconds 锁定 */
  expires_at: string | null
  confirmed_at: string | null
  /** 读取时计算的虚拟字段，仅用于前端提示；不等同于已写库的 timeout 状态 */
  is_likely_timeout: boolean
}

export interface ManagedAgentDeploymentDismissInput {
  prompt_artifact_keys?: string[]
  schedule_ids?: string[]
  comm_binding_ids?: string[]
}

export interface ManagedAgentDeploymentDismissResponse {
  message: string
  snapshot_id?: string
}

export type ManagedAgentDeploymentPhase = 'first_onboarding' | 'sync_required' | 'up_to_date'

export interface ManagedAgentDeploymentState {
  managed_agent_id: string
  deployment_phase: ManagedAgentDeploymentPhase
  /** 推荐脚本意图；up_to_date 时为 null */
  recommended_script_intent: ManagedAgentDeployScriptIntent | null
  is_first_onboarding: boolean
  has_confirmed_deployment: boolean
  needs_redeploy: boolean
  config_version: number
  deployed_config_version: number | null
  /** 平台配置是否满足生成脚本的前置条件 */
  deploy_ready: boolean
  runtime_registered: boolean
  message: string
}

/** 角色 Prompt 模板示例 */
export interface PromptTemplateItem {
  role: string
  label: string
  filename: string
  content: string
}

export interface PromptTemplateResponse {
  items: PromptTemplateItem[]
}
