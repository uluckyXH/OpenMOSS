-- OpenMOSS Cloudflare D1 schema
CREATE TABLE IF NOT EXISTS agent (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  description TEXT DEFAULT '',
  status TEXT DEFAULT 'active',
  api_key TEXT UNIQUE NOT NULL,
  total_score INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_role ON agent(role);
CREATE INDEX IF NOT EXISTS idx_agent_status ON agent(status);

CREATE TABLE IF NOT EXISTS task (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  type TEXT DEFAULT 'once',
  status TEXT DEFAULT 'planning',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_task_status ON task(status);

CREATE TABLE IF NOT EXISTS module (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(task_id) REFERENCES task(id)
);

CREATE TABLE IF NOT EXISTS sub_task (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  module_id TEXT,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  deliverable TEXT DEFAULT '',
  acceptance TEXT DEFAULT '',
  type TEXT DEFAULT 'once',
  status TEXT DEFAULT 'pending',
  priority TEXT DEFAULT 'medium',
  assigned_agent TEXT,
  current_session_id TEXT,
  rework_count INTEGER DEFAULT 0,
  recurring_config TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT,
  FOREIGN KEY(task_id) REFERENCES task(id),
  FOREIGN KEY(module_id) REFERENCES module(id),
  FOREIGN KEY(assigned_agent) REFERENCES agent(id)
);
CREATE INDEX IF NOT EXISTS idx_sub_task_status ON sub_task(status);
CREATE INDEX IF NOT EXISTS idx_sub_task_agent_status ON sub_task(assigned_agent,status);

CREATE TABLE IF NOT EXISTS review_record (
  id TEXT PRIMARY KEY,
  sub_task_id TEXT NOT NULL,
  reviewer_agent TEXT NOT NULL,
  round INTEGER NOT NULL,
  result TEXT NOT NULL,
  score INTEGER NOT NULL,
  issues TEXT DEFAULT '',
  comment TEXT DEFAULT '',
  rework_agent TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_review_sub_task ON review_record(sub_task_id);

CREATE TABLE IF NOT EXISTS reward_log (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  sub_task_id TEXT,
  reason TEXT NOT NULL,
  score_delta INTEGER NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reward_agent ON reward_log(agent_id);

CREATE TABLE IF NOT EXISTS activity_log (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  sub_task_id TEXT,
  action TEXT NOT NULL,
  summary TEXT DEFAULT '',
  session_id TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_activity_agent ON activity_log(agent_id);

CREATE TABLE IF NOT EXISTS request_log (
  id TEXT PRIMARY KEY,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  agent_id TEXT,
  agent_name TEXT,
  agent_role TEXT,
  request_body TEXT,
  response_status INTEGER
);
CREATE INDEX IF NOT EXISTS idx_request_agent ON request_log(agent_id);
CREATE INDEX IF NOT EXISTS idx_request_path ON request_log(path);

CREATE TABLE IF NOT EXISTS rule (
  id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  task_id TEXT,
  sub_task_id TEXT,
  content TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_session (
  token TEXT PRIMARY KEY,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS managed_agent (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL,
  description TEXT DEFAULT '',
  host_platform TEXT DEFAULT 'openclaw',
  deployment_mode TEXT DEFAULT 'create_sub_agent',
  host_access_mode TEXT DEFAULT 'local',
  status TEXT DEFAULT 'draft',
  runtime_agent_id TEXT,
  config_version INTEGER DEFAULT 1,
  deployed_config_version INTEGER,
  online_status TEXT,
  data_source TEXT DEFAULT 'cloudflare-d1',
  api_key TEXT,
  system_prompt_content TEXT DEFAULT '',
  persona_prompt_content TEXT DEFAULT '',
  identity_content TEXT DEFAULT '',
  host_render_strategy TEXT DEFAULT 'host_default',
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_managed_agent_role ON managed_agent(role);
CREATE INDEX IF NOT EXISTS idx_managed_agent_status ON managed_agent(status);

CREATE TABLE IF NOT EXISTS managed_agent_host_config (
  id TEXT PRIMARY KEY,
  managed_agent_id TEXT UNIQUE NOT NULL,
  host_platform TEXT DEFAULT 'openclaw',
  host_agent_identifier TEXT,
  workdir_path TEXT,
  host_config_payload_masked TEXT,
  host_metadata_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS managed_agent_schedule (
  id TEXT PRIMARY KEY,
  managed_agent_id TEXT NOT NULL,
  name TEXT NOT NULL,
  enabled INTEGER DEFAULT 1,
  schedule_type TEXT NOT NULL,
  schedule_expr TEXT NOT NULL,
  timeout_seconds INTEGER DEFAULT 300,
  model_override TEXT,
  execution_options_json TEXT,
  schedule_message_content TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS managed_agent_comm_binding (
  id TEXT PRIMARY KEY,
  managed_agent_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  binding_key TEXT NOT NULL,
  display_name TEXT,
  enabled INTEGER DEFAULT 1,
  routing_policy_json TEXT,
  metadata_json TEXT,
  config_payload_masked TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS managed_agent_bootstrap_token (
  id TEXT PRIMARY KEY,
  managed_agent_id TEXT NOT NULL,
  token TEXT NOT NULL,
  purpose TEXT NOT NULL,
  scope_json TEXT,
  expires_at TEXT NOT NULL,
  used_at TEXT,
  revoked_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS managed_agent_deployment_snapshot (
  id TEXT PRIMARY KEY,
  managed_agent_id TEXT NOT NULL,
  script_intent TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  changeset_json TEXT,
  confirmation_payload_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT,
  confirmed_at TEXT,
  dismissed_at TEXT
);
