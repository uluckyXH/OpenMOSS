const CORS_HEADERS = { "access-control-allow-origin": "*", "access-control-allow-headers": "authorization,content-type,x-admin-token,x-registration-token,Authorization,Content-Type,X-Admin-Token,X-Registration-Token", "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS" };
const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", ...CORS_HEADERS };
const HTML_HEADERS = { "content-type": "text/html; charset=utf-8" };
const TEXT_HEADERS = { "content-type": "text/plain; charset=utf-8", ...CORS_HEADERS };

function uid(prefix = "") {
  return prefix + crypto.randomUUID();
}
function nowIso() { return new Date().toISOString(); }
function json(data, status = 200) { return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS }); }
function text(data, status = 200) { return new Response(data, { status, headers: TEXT_HEADERS }); }
function html(data, status = 200) { return new Response(data, { status, headers: HTML_HEADERS }); }
async function bodyJson(req) { try { return await req.json(); } catch { return {}; } }
function getBearer(req) { const h = req.headers.get("authorization") || ""; return h.startsWith("Bearer ") ? h.slice(7) : null; }
function getAdminToken(req) { return req.headers.get("x-admin-token") || getBearer(req); }
function projectName(env) { return env.OPENMOSS_PROJECT_NAME || "OpenMOSS Cloudflare"; }
function registrationToken(env) { return env.OPENMOSS_REGISTRATION_TOKEN || "openclaw-register-2024"; }
function adminPassword(env) { return 'admin123'; }
function publicFeed(env) { return String(env.OPENMOSS_PUBLIC_FEED || "true") === "true"; }

async function verifyAdmin(req, env) {
  const token = getAdminToken(req);
  if (!token) return false;
  if (token === adminPassword(env)) return true;
  const row = await env.DB.prepare("SELECT token FROM admin_session WHERE token=?").bind(token).first();
  return !!row;
}
async function requireAdmin(req, env) { if (!(await verifyAdmin(req, env))) throw Object.assign(new Error("Admin auth required"), { status: 403 }); }
async function getAgent(req, env) {
  const key = getBearer(req);
  if (!key) return null;
  return await env.DB.prepare("SELECT * FROM agent WHERE api_key=? AND status='active'").bind(key).first();
}
async function requireAgent(req, env) {
  const agent = await getAgent(req, env);
  if (!agent) throw Object.assign(new Error("Invalid agent API key"), { status: 401 });
  return agent;
}
function requireRole(agent, roles) {
  const set = Array.isArray(roles) ? roles : [roles];
  if (!set.includes(agent.role)) throw Object.assign(new Error(`Role ${agent.role} cannot perform this action`), { status: 403 });
}
async function logRequest(req, env, agent, status, body) {
  if (!req.url.includes('/api/') || !agent) return;
  try {
    await env.DB.prepare(`INSERT INTO request_log (id,timestamp,method,path,agent_id,agent_name,agent_role,request_body,response_status) VALUES (?,?,?,?,?,?,?,?,?)`)
      .bind(uid(), nowIso(), req.method, new URL(req.url).pathname, agent.id, agent.name, agent.role, body ? JSON.stringify(body).slice(0,10000) : null, status).run();
  } catch (e) { console.log('request log failed', e.message); }
}


function managedAgentRow(row) {
  if (!row) return null;
  return {
    id: row.id, name: row.name, slug: row.slug, role: row.role, description: row.description || '',
    host_platform: row.host_platform || 'openclaw', deployment_mode: row.deployment_mode || 'create_sub_agent', host_access_mode: row.host_access_mode || 'local',
    status: row.status || 'draft', runtime_agent_id: row.runtime_agent_id || null, config_version: row.config_version || 1, deployed_config_version: row.deployed_config_version || null,
    needs_redeploy: (row.deployed_config_version || 0) < (row.config_version || 1), online_status: row.online_status || null, data_source: row.data_source || 'cloudflare-d1',
    created_at: row.created_at, updated_at: row.updated_at,
    readiness: { host_config: true, prompt_asset: true, schedules_count: 0, comm_bindings_count: 0, deploy_ready: true },
    runtime_identity: { registered: !!row.runtime_agent_id, runtime_agent_id: row.runtime_agent_id || null, api_key_masked: row.api_key ? row.api_key.slice(0,6)+'…'+row.api_key.slice(-4) : null }
  };
}
function defaultPrompt(role, name='Agent') {
  return `# ${name}\n\n你是 OpenMOSS 的 ${role} 角色 Agent。\n\n## 工作方式\n- 遵循任务上下文\n- 主动记录进展\n- 交付可验证结果\n`;
}
function promptMetaFromRow(row) {
  return { slug: row.slug, filename: `${row.slug}.md`, name: row.name, role: row.role, description: row.description || '', created_at: row.created_at, example: false, has_frontmatter: false, status: 'ok' };
}
function templateContent(role) {
  const map={planner:'规划任务、拆解模块、分配子任务。',executor:'领取任务、执行实现、提交交付物。',reviewer:'审查交付质量、给出通过或返工意见。',patrol:'巡查进度、发现阻塞、输出告警。'};
  return `# ${role}\n\n${map[role] || 'OpenMOSS Agent 角色提示词。'}\n`;
}
function hostPlatformsMeta() {
  return { items: [{ key:'openclaw', label:'OpenClaw', description:'OpenClaw 子 Agent / 主 Agent', access_modes:['local'], deployment_modes:['create_sub_agent','bind_existing_agent','bind_main_agent'], capabilities:{renderer:true,bootstrap_script:false,skill_bundle:false,prompt_preview:true,schedule:true,comm_binding:true}, supported_comm_providers:['feishu','wechat','telegram','slack','webhook'], ui_hints:{ host_config:{description:'Cloudflare 版本仅保存配置，不直接控制宿主进程。', fields:[{key:'host_agent_identifier',label:'宿主 Agent ID',type:'text',required:false},{key:'workdir_path',label:'工作目录',type:'text',required:false}]}, prompt:{description:'编辑 Agent 提示词资产。', render_strategies:[{value:'host_default',label:'宿主默认',description:'由宿主按默认规则渲染',is_default:true}], sections:[{key:'system_prompt_content',label:'系统提示词',required:true,description:'核心职责和规则'},{key:'persona_prompt_content',label:'人格提示词',required:false,description:'风格/人格补充'},{key:'identity_content',label:'身份文件',required:false,description:'身份元信息'}]}, schedule:{description:'Cloudflare 版本暂存计划配置。',supported_types:['interval','cron'],default_expr:'0 * * * *',default_timeout:300}, comm:{description:'Cloudflare 版本暂存通讯绑定。'} } }] };
}


function renderArtifacts(row, draft = {}) {
  const system = draft.system_prompt_content ?? row.system_prompt_content ?? defaultPrompt(row.role, row.name);
  const persona = draft.persona_prompt_content ?? row.persona_prompt_content ?? '';
  const identity = draft.identity_content ?? row.identity_content ?? '';
  const strategy = draft.host_render_strategy ?? row.host_render_strategy ?? 'host_default';
  const content = [system, persona, identity].filter(Boolean).join('\n\n---\n\n');
  return { host_platform: row.host_platform || 'openclaw', host_render_strategy: strategy, artifacts: [{ name: `${row.slug || row.id}.md`, content }] };
}
function deploymentState(row) {
  const cv = Number(row.config_version || 1), dv = row.deployed_config_version == null ? null : Number(row.deployed_config_version);
  return { managed_agent_id: row.id, config_version: cv, deployed_config_version: dv, needs_redeploy: dv == null || dv < cv, status: row.status || 'draft', deploy_ready: Boolean((row.system_prompt_content || '').trim()) };
}
function bootstrapScript(origin, row, token) {
  return `#!/usr/bin/env bash\nset -euo pipefail\nBASE_URL=${JSON.stringify(origin)}\nMANAGED_AGENT_ID=${JSON.stringify(row.id)}\nBOOTSTRAP_TOKEN=${JSON.stringify(token)}\necho \"OpenMOSS Cloudflare bootstrap for ${row.name}\"\necho \"$BASE_URL\"\n`;
}

function page(items, url) {
  const currentPage = Math.max(1, Number(url.searchParams.get('page') || 1));
  const pageSize = Math.min(100, Math.max(1, Number(url.searchParams.get('page_size') || items.length || 20)));
  const total = items.length;
  const start = (currentPage - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), total, page: currentPage, page_size: pageSize, total_pages: Math.max(1, Math.ceil(total / pageSize)), has_more: currentPage * pageSize < total };
}

function pageParams(url) {
  const page = Math.max(1, Number(url.searchParams.get('page') || 1));
  const pageSize = Math.min(100, Math.max(0, Number(url.searchParams.get('page_size') || 0)));
  return { page, pageSize };
}
async function listQuery(env, sql, binds = [], url) {
  const { page, pageSize } = pageParams(url);
  if (pageSize > 0) {
    const offset = (page - 1) * pageSize;
    const countSql = `SELECT count(*) as c FROM (${sql}) x`;
    const total = (await env.DB.prepare(countSql).bind(...binds).first()).c || 0;
    const rows = (await env.DB.prepare(`${sql} LIMIT ? OFFSET ?`).bind(...binds, pageSize, offset).all()).results || [];
    return { items: rows, total, page, page_size: pageSize, total_pages: Math.max(1, Math.ceil(total / pageSize)), has_more: page * pageSize < total };
  }
  return (await env.DB.prepare(sql).bind(...binds).all()).results || [];
}

async function initSchema(env) {
  const stmts = SCHEMA_SQL.split(';').map(s => s.trim()).filter(Boolean);
  for (const s of stmts) await env.DB.prepare(s).run();
}

async function routeApi(req, env, ctx) {
  const url = new URL(req.url);
  const path = url.pathname.replace(/^\/api/, '') || '/';
  let agent = null;
  let reqBody = null;

  if (path === '/health') return json({ ok: true, runtime: 'cloudflare-workers', project: projectName(env), time: nowIso() });
  if (path === '/version') return json({ name: 'OpenMOSS Cloudflare', version: '2.0.0-cloudflare', runtime: 'cloudflare-workers' });
  if (path === '/setup/status') return json({ initialized: true, has_external_url: true });
  if (path === '/setup/initialize' && req.method === 'POST') return json({ ok: true, initialized: true });
  if (path === '/webui/version') return json({ current_version: '0.0.1', latest_version: '0.0.1', update_available: false, update_type: 'none', checked_at: nowIso() });
  if (path === '/webui/version/check') return json({ current_version: '0.0.1', latest_version: '0.0.1', update_available: false, update_type: 'none', checked_at: nowIso() });
  if (path === '/admin/webui/update' && req.method === 'POST') return json({ ok: true, message: 'Cloudflare Pages deployment is managed by Wrangler/Pages.' });
  if (path === '/config/notification') { agent = await requireAgent(req, env); return json({ enabled: false, channels: [], events: [] }); }

  if (path === '/admin/login' && req.method === 'POST') {
    reqBody = await bodyJson(req);
    if (String(reqBody.password || '').trim() !== adminPassword(env)) return json({ detail: '密码错误' }, 403);
    // Cloudflare Workers should not depend on a writable server-side session for admin login.
    // verifyAdmin() accepts the admin password token, so the original WebUI can keep storing
    // the returned token while we avoid D1 session-write failures during cross-origin Pages login.
    return json({ token: adminPassword(env), message: '登录成功' });
  }
  if (path === '/admin/config' && req.method === 'GET') { await requireAdmin(req, env); return json({ project: { name: projectName(env) }, agent: { allow_registration: true, registration_token: registrationToken(env) }, webui: { public_feed: publicFeed(env) }, server: { external_url: url.origin }, database: { type: 'cloudflare-d1' } }); }

  if (path === '/admin/config' && req.method === 'PUT') { await requireAdmin(req, env); return json({ok:true, message:'Cloudflare configuration is managed by wrangler vars/secrets.'}); }
  if (path === '/admin/config/password' && req.method === 'PUT') { await requireAdmin(req, env); return json({ok:true, message:'Cloudflare demo password is fixed to admin123 in this build.'}); }

  if (path === '/admin/dashboard/overview' && req.method === 'GET') { await requireAdmin(req, env); return json(await dashboardOverview(env)); }
  
  if (path === '/admin/dashboard/highlights' && req.method === 'GET') { await requireAdmin(req, env); return json({ generated_at: nowIso(), limit: Number(url.searchParams.get('limit') || 5), inactive_hours: Number(url.searchParams.get('inactive_hours') || 24), blocked_sub_tasks: [], pending_review_sub_tasks: [], busy_agents: [], low_activity_agents: [], recent_reviews: [] }); }
  if (path === '/admin/dashboard/trends' && req.method === 'GET') { await requireAdmin(req, env); const days=Number(url.searchParams.get('days')||14); return json({ generated_at: nowIso(), days, start_date: nowIso().slice(0,10), end_date: nowIso().slice(0,10), sub_task_created_trend: [], sub_task_completed_trend: [], review_trend: [], score_delta_trend: [], request_trend: [], activity_trend: [] }); }

  if (path === '/rules' && req.method === 'GET') { agent = await requireAgent(req, env); const scope=url.searchParams.get('scope')||'global'; const rows=(await env.DB.prepare("SELECT * FROM rule WHERE scope=? OR scope='global' ORDER BY created_at ASC").bind(scope).all()).results||[]; return json({ scope, rules: rows, merged_content: rows.map(r=>r.content).join('\n\n') }); }
  if (path === '/rules/list' && req.method === 'GET') { await requireAdmin(req, env); const scope=url.searchParams.get('scope'); const rows=(await env.DB.prepare(`SELECT * FROM rule ${scope?'WHERE scope=?':''} ORDER BY created_at DESC`).bind(...(scope?[scope]:[])).all()).results||[]; return json(rows); }
  const ruleOne = path.match(/^\/rules\/([^/]+)$/);
  if (ruleOne && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM rule WHERE id=?").bind(ruleOne[1]).first(); return row?json(row):json({detail:'Rule not found'},404); }
  if (path === '/rules' && req.method === 'POST') { await requireAdmin(req, env); reqBody=await bodyJson(req); const id=uid('rule_'), t=nowIso(); await env.DB.prepare("INSERT INTO rule (id,scope,task_id,sub_task_id,content,created_at,updated_at) VALUES (?,?,?,?,?,?,?)").bind(id,reqBody.scope||'global',reqBody.task_id||null,reqBody.sub_task_id||null,reqBody.content||'',t,t).run(); return json(await env.DB.prepare("SELECT * FROM rule WHERE id=?").bind(id).first()); }
  if (ruleOne && req.method === 'PUT') { await requireAdmin(req, env); reqBody=await bodyJson(req); await env.DB.prepare("UPDATE rule SET content=?, updated_at=? WHERE id=?").bind(reqBody.content||'',nowIso(),ruleOne[1]).run(); return json(await env.DB.prepare("SELECT * FROM rule WHERE id=?").bind(ruleOne[1]).first()); }
  if (ruleOne && req.method === 'DELETE') { await requireAdmin(req, env); await env.DB.prepare("DELETE FROM rule WHERE id=?").bind(ruleOne[1]).run(); return json({ok:true}); }

  if (path === '/admin/scores/summary' && req.method === 'GET') { await requireAdmin(req, env); const rows=(await env.DB.prepare("SELECT total_score FROM agent").all()).results||[]; const scores=rows.map(r=>Number(r.total_score||0)); return json({ total_agents: scores.length, positive_score_agents: scores.filter(x=>x>0).length, zero_score_agents: scores.filter(x=>x===0).length, negative_score_agents: scores.filter(x=>x<0).length, top_score: Math.max(0,...scores), average_score: scores.length? scores.reduce((a,b)=>a+b,0)/scores.length:0, last_score_at: null }); }
  if (path === '/admin/scores/logs' && req.method === 'GET') { await requireAdmin(req, env); const rows=(await env.DB.prepare("SELECT r.*, a.name AS agent_name FROM reward_log r LEFT JOIN agent a ON a.id=r.agent_id ORDER BY r.created_at DESC").all()).results||[]; return json(page(rows, url)); }
  if (path === '/admin/scores/adjust' && req.method === 'POST') { await requireAdmin(req, env); reqBody=await bodyJson(req); const id=uid(); await env.DB.prepare("INSERT INTO reward_log (id,agent_id,sub_task_id,reason,score_delta,created_at) VALUES (?,?,?,?,?,?)").bind(id,reqBody.agent_id,reqBody.sub_task_id||null,reqBody.reason||'manual',Number(reqBody.score_delta||0),nowIso()).run(); await env.DB.prepare("UPDATE agent SET total_score=total_score+? WHERE id=?").bind(Number(reqBody.score_delta||0),reqBody.agent_id).run(); return json({ok:true,id}); }
  if (path === '/admin/prompts/templates') { await requireAdmin(req, env); return json(['planner','executor','reviewer','patrol'].map(role=>({role,filename:`${role}.md`,content:templateContent(role)}))); }
  const pt = path.match(/^\/admin\/prompts\/templates\/([^/]+)$/);
  if (pt && req.method === 'GET') { await requireAdmin(req, env); return json({role:pt[1],filename:`${pt[1]}.md`,content:templateContent(pt[1])}); }
  if (pt && req.method === 'PUT') { await requireAdmin(req, env); return json({ok:true, role:pt[1], message:'Cloudflare compact backend keeps built-in role templates read-only for now.'}); }
  if (path === '/admin/prompts/agents' && req.method === 'GET') { await requireAdmin(req, env); const rows=(await env.DB.prepare("SELECT * FROM managed_agent ORDER BY created_at DESC").all()).results||[]; return json(rows.map(promptMetaFromRow)); }
  if (path === '/admin/prompts/agents' && req.method === 'POST') { await requireAdmin(req, env); reqBody=await bodyJson(req); const id=uid('ma_'); const t=nowIso(); await env.DB.prepare(`INSERT INTO managed_agent (id,name,slug,role,description,host_platform,deployment_mode,host_access_mode,status,system_prompt_content,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`).bind(id,reqBody.name,reqBody.slug,reqBody.role,reqBody.description||'','openclaw','create_sub_agent','local','draft',reqBody.content||defaultPrompt(reqBody.role,reqBody.name),t,t).run(); return json(promptMetaFromRow(await env.DB.prepare("SELECT * FROM managed_agent WHERE slug=?").bind(reqBody.slug).first())); }
  const pa = path.match(/^\/admin\/prompts\/agents\/([^/]+)$/);
  if (pa && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE slug=?").bind(pa[1]).first(); return row?json({...promptMetaFromRow(row), content:row.system_prompt_content||defaultPrompt(row.role,row.name)}):json({detail:'Prompt agent not found'},404); }
  if (pa && req.method === 'PUT') { await requireAdmin(req, env); reqBody=await bodyJson(req); await env.DB.prepare("UPDATE managed_agent SET name=COALESCE(?,name), role=COALESCE(?,role), description=COALESCE(?,description), system_prompt_content=COALESCE(?,system_prompt_content), config_version=config_version+1, updated_at=? WHERE slug=?").bind(reqBody.name??null,reqBody.role??null,reqBody.description??null,reqBody.content??null,nowIso(),pa[1]).run(); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE slug=?").bind(pa[1]).first(); return json({...promptMetaFromRow(row), content:row.system_prompt_content||''}); }
  if (pa && req.method === 'DELETE') { await requireAdmin(req, env); await env.DB.prepare("DELETE FROM managed_agent WHERE slug=?").bind(pa[1]).run(); return json({ok:true}); }
  const pc = path.match(/^\/admin\/prompts\/compose\/([^/]+)$/);
  if (pc) { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE slug=?").bind(pc[1]).first(); return row?json({slug:pc[1], prompt:[row.system_prompt_content,row.persona_prompt_content,row.identity_content].filter(Boolean).join('\n\n---\n\n')}):json({detail:'Not found'},404); }
  const po = path.match(/^\/admin\/prompts\/onboarding\/([^/]+)$/);
  if (po) { await requireAdmin(req, env); return json({role:po[1], content:`# ${po[1]} onboarding\n\n使用 Cloudflare Worker API 与 OpenMOSS 协作。`}); }

  
  if (path === '/admin/review-records' && req.method === 'GET') { await requireAdmin(req, env); const rows=(await env.DB.prepare(`SELECT r.*, s.task_id, t.name AS task_name, s.module_id, m.name AS module_name, s.name AS sub_task_name, a.name AS reviewer_agent_name, ra.name AS rework_agent_name FROM review_record r LEFT JOIN sub_task s ON s.id=r.sub_task_id LEFT JOIN task t ON t.id=s.task_id LEFT JOIN module m ON m.id=s.module_id LEFT JOIN agent a ON a.id=r.reviewer_agent LEFT JOIN agent ra ON ra.id=r.rework_agent ORDER BY r.created_at DESC`).all()).results||[]; return json(page(rows, url)); }
  if (path.match(/^\/admin\/review-records\/[^/]+$/) && req.method === 'GET') { await requireAdmin(req, env); return json({detail:'Not implemented in Cloudflare compact backend'},404); }
  if (path === '/admin/managed-agents/meta/host-platforms') { await requireAdmin(req, env); return json(hostPlatformsMeta()); }
  if (path === '/admin/managed-agents/meta/prompt-templates') { await requireAdmin(req, env); const role=url.searchParams.get('role'); const roles=role?[role]:['planner','executor','reviewer','patrol']; return json({ items: roles.map(r=>({role:r,name:r,content:templateContent(r)})) }); }
  if (path.match(/^\/admin\/managed-agents\/meta\/host-platforms\/[^/]+\/comm-providers\/[^/]+\/schema$/)) { await requireAdmin(req, env); return json({ provider: path.split('/').at(-2), label:'Webhook', description:'Cloudflare 兼容占位 schema', supports_multiple_bindings:true, fields:[] }); }
  if (path.match(/^\/admin\/managed-agents\/meta\/host-platforms\/[^/]+\/comm-providers\/[^/]+\/validate$/) && req.method === 'POST') { await requireAdmin(req, env); return json({ valid:true, errors:[] }); }
  if (path === '/admin/managed-agents' && req.method === 'GET') { await requireAdmin(req, env); const rows=(await env.DB.prepare("SELECT * FROM managed_agent ORDER BY created_at DESC").all()).results||[]; return json(page(rows.map(managedAgentRow), url)); }
  if (path === '/admin/managed-agents' && req.method === 'POST') { await requireAdmin(req, env); reqBody=await bodyJson(req); const id=uid('ma_'); const t=nowIso(); const apiKey=uid('ak_'); await env.DB.prepare(`INSERT INTO managed_agent (id,name,slug,role,description,host_platform,deployment_mode,host_access_mode,status,runtime_agent_id,api_key,system_prompt_content,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(id,reqBody.name,reqBody.slug,reqBody.role,reqBody.description||'',reqBody.host_platform||'openclaw',reqBody.deployment_mode||'create_sub_agent',reqBody.host_access_mode||'local','draft',reqBody.host_agent_identifier||null,apiKey,defaultPrompt(reqBody.role,reqBody.name),t,t).run(); return json(managedAgentRow(await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(id).first())); }
  const ma = path.match(/^\/admin\/managed-agents\/([^/]+)$/);
  if (ma && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(ma[1]).first(); return row?json(managedAgentRow(row)):json({detail:'Managed agent not found'},404); }
  if (ma && req.method === 'PUT') { await requireAdmin(req, env); reqBody=await bodyJson(req); await env.DB.prepare("UPDATE managed_agent SET name=COALESCE(?,name), description=COALESCE(?,description), host_platform=COALESCE(?,host_platform), deployment_mode=COALESCE(?,deployment_mode), host_access_mode=COALESCE(?,host_access_mode), status=COALESCE(?,status), config_version=config_version+1, updated_at=? WHERE id=?").bind(reqBody.name??null,reqBody.description??null,reqBody.host_platform??null,reqBody.deployment_mode??null,reqBody.host_access_mode??null,reqBody.status??null,nowIso(),ma[1]).run(); return json(managedAgentRow(await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(ma[1]).first())); }
  if (ma && req.method === 'DELETE') { await requireAdmin(req, env); await env.DB.prepare("DELETE FROM managed_agent WHERE id=?").bind(ma[1]).run(); return json({ok:true}); }
  const maPrompt = path.match(/^\/admin\/managed-agents\/([^/]+)\/prompt-asset$/);
  if (maPrompt && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(maPrompt[1]).first(); if(!row)return json({detail:'Not found'},404); return json({ id:'pa_'+row.id, managed_agent_id:row.id, template_role:row.role, system_prompt_content:row.system_prompt_content||defaultPrompt(row.role,row.name), persona_prompt_content:row.persona_prompt_content||'', identity_content:row.identity_content||'', host_render_strategy:row.host_render_strategy||'host_default', authority_source:'cloudflare-d1', notes:row.notes||null, updated_at:row.updated_at }); }
  if (maPrompt && req.method === 'PUT') { await requireAdmin(req, env); reqBody=await bodyJson(req); await env.DB.prepare("UPDATE managed_agent SET system_prompt_content=COALESCE(?,system_prompt_content), persona_prompt_content=COALESCE(?,persona_prompt_content), identity_content=COALESCE(?,identity_content), host_render_strategy=COALESCE(?,host_render_strategy), notes=COALESCE(?,notes), config_version=config_version+1, updated_at=? WHERE id=?").bind(reqBody.system_prompt_content??null,reqBody.persona_prompt_content??null,reqBody.identity_content??null,reqBody.host_render_strategy??null,reqBody.notes??null,nowIso(),maPrompt[1]).run(); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(maPrompt[1]).first(); return json({ id:'pa_'+row.id, managed_agent_id:row.id, template_role:row.role, system_prompt_content:row.system_prompt_content||'', persona_prompt_content:row.persona_prompt_content||'', identity_content:row.identity_content||'', host_render_strategy:row.host_render_strategy||'host_default', authority_source:'cloudflare-d1', notes:row.notes||null, updated_at:row.updated_at }); }
  if (path.match(/^\/admin\/managed-agents\/([^/]+)\/prompt-asset\/reset-from-template$/) && req.method === 'POST') { await requireAdmin(req, env); const id=path.split('/')[3]; const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(id).first(); await env.DB.prepare("UPDATE managed_agent SET system_prompt_content=?, config_version=config_version+1, updated_at=? WHERE id=?").bind(defaultPrompt(row.role,row.name),nowIso(),id).run(); return json({ok:true}); }
  const maPreview = path.match(/^\/admin\/managed-agents\/([^/]+)\/prompt-asset\/render-preview$/);
  if (maPreview && req.method === 'POST') { await requireAdmin(req, env); reqBody=await bodyJson(req); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(maPreview[1]).first(); return row?json(renderArtifacts(row, reqBody)):json({detail:'Not found'},404); }
  const maHost = path.match(/^\/admin\/managed-agents\/([^/]+)\/host-config$/);
  if (maHost && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent_host_config WHERE managed_agent_id=?").bind(maHost[1]).first(); return json(row || {id:'hc_'+maHost[1],managed_agent_id:maHost[1],host_platform:'openclaw',host_agent_identifier:null,workdir_path:null,host_config_payload_masked:null,host_metadata_json:null,created_at:nowIso(),updated_at:nowIso()}); }
  if (maHost && (req.method === 'PUT' || req.method === 'POST')) { await requireAdmin(req, env); reqBody=await bodyJson(req); const t=nowIso(); const old=await env.DB.prepare("SELECT id FROM managed_agent_host_config WHERE managed_agent_id=?").bind(maHost[1]).first(); if(old) await env.DB.prepare("UPDATE managed_agent_host_config SET host_agent_identifier=?, workdir_path=?, host_config_payload_masked=?, host_metadata_json=?, updated_at=? WHERE managed_agent_id=?").bind(reqBody.host_agent_identifier||null,reqBody.workdir_path||null,reqBody.host_config_payload?'***':null,reqBody.host_metadata_json||null,t,maHost[1]).run(); else await env.DB.prepare("INSERT INTO managed_agent_host_config (id,managed_agent_id,host_platform,host_agent_identifier,workdir_path,host_config_payload_masked,host_metadata_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)").bind(uid('hc_'),maHost[1],'openclaw',reqBody.host_agent_identifier||null,reqBody.workdir_path||null,reqBody.host_config_payload?'***':null,reqBody.host_metadata_json||null,t,t).run(); return json(await env.DB.prepare("SELECT * FROM managed_agent_host_config WHERE managed_agent_id=?").bind(maHost[1]).first()); }
  const maSchedules = path.match(/^\/admin\/managed-agents\/([^/]+)\/schedules$/);
  if (maSchedules && req.method === 'GET') { await requireAdmin(req, env); return json((await env.DB.prepare("SELECT * FROM managed_agent_schedule WHERE managed_agent_id=? ORDER BY created_at DESC").bind(maSchedules[1]).all()).results||[]); }
  if (maSchedules && req.method === 'POST') { await requireAdmin(req, env); reqBody=await bodyJson(req); const id=uid('sch_'), t=nowIso(); await env.DB.prepare("INSERT INTO managed_agent_schedule (id,managed_agent_id,name,enabled,schedule_type,schedule_expr,timeout_seconds,model_override,execution_options_json,schedule_message_content,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)").bind(id,maSchedules[1],reqBody.name,reqBody.enabled===false?0:1,reqBody.schedule_type,reqBody.schedule_expr,Number(reqBody.timeout_seconds||300),reqBody.model_override||null,reqBody.execution_options_json||null,reqBody.schedule_message_content||'',t,t).run(); return json(await env.DB.prepare("SELECT * FROM managed_agent_schedule WHERE id=?").bind(id).first()); }
  const maScheduleOne = path.match(/^\/admin\/managed-agents\/([^/]+)\/schedules\/([^/]+)$/);
  if (maScheduleOne && req.method === 'DELETE') { await requireAdmin(req, env); await env.DB.prepare("DELETE FROM managed_agent_schedule WHERE id=? AND managed_agent_id=?").bind(maScheduleOne[2],maScheduleOne[1]).run(); return json({ok:true}); }
  const maComms = path.match(/^\/admin\/managed-agents\/([^/]+)\/comm-bindings$/);
  if (maComms && req.method === 'GET') { await requireAdmin(req, env); return json((await env.DB.prepare("SELECT * FROM managed_agent_comm_binding WHERE managed_agent_id=? ORDER BY created_at DESC").bind(maComms[1]).all()).results||[]); }
  if (maComms && req.method === 'POST') { await requireAdmin(req, env); reqBody=await bodyJson(req); const id=uid('cb_'), t=nowIso(); await env.DB.prepare("INSERT INTO managed_agent_comm_binding (id,managed_agent_id,provider,binding_key,display_name,enabled,routing_policy_json,metadata_json,config_payload_masked,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)").bind(id,maComms[1],reqBody.provider,reqBody.binding_key,reqBody.display_name||null,reqBody.enabled===false?0:1,reqBody.routing_policy_json||null,reqBody.metadata_json||null,reqBody.config_payload?'***':null,t,t).run(); return json(await env.DB.prepare("SELECT * FROM managed_agent_comm_binding WHERE id=?").bind(id).first()); }
  const maBoot = path.match(/^\/admin\/managed-agents\/([^/]+)\/bootstrap-tokens$/);
  if (maBoot && req.method === 'GET') { await requireAdmin(req, env); return json((await env.DB.prepare("SELECT id,managed_agent_id,purpose,scope_json,expires_at,used_at,revoked_at,created_at FROM managed_agent_bootstrap_token WHERE managed_agent_id=? ORDER BY created_at DESC").bind(maBoot[1]).all()).results||[]); }
  if (maBoot && req.method === 'POST') { await requireAdmin(req, env); reqBody=await bodyJson(req); const id=uid('bt_'), token=uid('boot_'), t=nowIso(), exp=new Date(Date.now()+Number(reqBody.ttl_seconds||3600)*1000).toISOString(); await env.DB.prepare("INSERT INTO managed_agent_bootstrap_token (id,managed_agent_id,token,purpose,scope_json,expires_at,created_at) VALUES (?,?,?,?,?,?,?)").bind(id,maBoot[1],token,reqBody.purpose||'download_script',reqBody.scope_json||null,exp,t).run(); return json({id,managed_agent_id:maBoot[1],token,purpose:reqBody.purpose||'download_script',expires_at:exp,created_at:t}); }
  const maBootScript = path.match(/^\/admin\/managed-agents\/([^/]+)\/bootstrap-script$/);
  if (maBootScript && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(maBootScript[1]).first(); return row?json({script:bootstrapScript(url.origin,row,uid('boot_')),register_token_id:'inline',register_token_expires_at:new Date(Date.now()+3600*1000).toISOString()}):json({detail:'Not found'},404); }
  const maOnboard = path.match(/^\/admin\/managed-agents\/([^/]+)\/onboarding-message$/);
  if (maOnboard && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(maOnboard[1]).first(); return row?json({message:`请使用 ${url.origin} 接入 ${row.name}`,curl_command:`curl ${url.origin}/api/health`,download_token_id:'inline',download_token_expires_at:new Date(Date.now()+3600*1000).toISOString()}):json({detail:'Not found'},404); }
  const maDeployState = path.match(/^\/admin\/managed-agents\/([^/]+)\/deployment-state$/);
  if (maDeployState && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(maDeployState[1]).first(); return row?json(deploymentState(row)):json({detail:'Not found'},404); }
  const maDeployPreview = path.match(/^\/admin\/managed-agents\/([^/]+)\/deploy-preview$/);
  if (maDeployPreview && req.method === 'POST') { await requireAdmin(req, env); return json({changeset:[{resource_type:'prompt',change_type:'update',resource_id:maDeployPreview[1],label:'同步 Agent 配置',enabled:true}],warnings:[]}); }
  const maDeployScript = path.match(/^\/admin\/managed-agents\/([^/]+)\/deploy-script$/);
  if (maDeployScript && req.method === 'POST') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM managed_agent WHERE id=?").bind(maDeployScript[1]).first(); return row?json({script:bootstrapScript(url.origin,row,uid('boot_')),snapshot_id:uid('snap_'),changeset:[{resource_type:'prompt',change_type:'update',resource_id:row.id,label:'同步 Agent 配置',enabled:true}]}):json({detail:'Not found'},404); }
  const maSnaps = path.match(/^\/admin\/managed-agents\/([^/]+)\/deployment-snapshots$/);
  if (maSnaps && req.method === 'GET') { await requireAdmin(req, env); return json((await env.DB.prepare("SELECT * FROM managed_agent_deployment_snapshot WHERE managed_agent_id=? ORDER BY created_at DESC").bind(maSnaps[1]).all()).results||[]); }
  const maDismiss = path.match(/^\/admin\/managed-agents\/([^/]+)\/deployment-snapshot\/dismiss$/);
  if (maDismiss && req.method === 'POST') { await requireAdmin(req, env); return json({ok:true,dismissed:true}); }
  if (path.startsWith('/admin/managed-agents/')) { await requireAdmin(req, env); return json({ ok:true }); }


  // Admin detail routes from original backend
  let adminAgentOne = path.match(/^\/admin\/agents\/([^/]+)$/);
  if (adminAgentOne && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT id,name,role,description,status,total_score,created_at FROM agent WHERE id=?").bind(adminAgentOne[1]).first(); return row?json(row):json({detail:'Agent not found'},404); }
  let adminTaskOne = path.match(/^\/admin\/tasks\/([^/]+)$/);
  if (adminTaskOne && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM task WHERE id=?").bind(adminTaskOne[1]).first(); return row?json(row):json({detail:'Task not found'},404); }
  let adminTaskModules = path.match(/^\/admin\/tasks\/([^/]+)\/modules$/);
  if (adminTaskModules && req.method === 'GET') { await requireAdmin(req, env); return json(page((await env.DB.prepare("SELECT * FROM module WHERE task_id=? ORDER BY created_at DESC").bind(adminTaskModules[1]).all()).results||[], url)); }
  let adminModuleOne = path.match(/^\/admin\/modules\/([^/]+)$/);
  if (adminModuleOne && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM module WHERE id=?").bind(adminModuleOne[1]).first(); return row?json(row):json({detail:'Module not found'},404); }
  if (path === '/admin/sub-tasks' && req.method === 'GET') { await requireAdmin(req, env); return json(await listQuery(env, "SELECT * FROM sub_task ORDER BY created_at DESC", [], url)); }
  let adminSubOne = path.match(/^\/admin\/sub-tasks\/([^/]+)$/);
  if (adminSubOne && req.method === 'GET') { await requireAdmin(req, env); const row=await env.DB.prepare("SELECT * FROM sub_task WHERE id=?").bind(adminSubOne[1]).first(); return row?json(row):json({detail:'Sub task not found'},404); }
  let adminTaskSubs = path.match(/^\/admin\/tasks\/([^/]+)\/sub-tasks$/);
  if (adminTaskSubs && req.method === 'GET') { await requireAdmin(req, env); return json(await listQuery(env, "SELECT * FROM sub_task WHERE task_id=? ORDER BY created_at DESC", [adminTaskSubs[1]], url)); }

  if (path === '/admin/agents' && req.method === 'GET') { await requireAdmin(req, env); return json(await listAdminAgents(env, url)); }
  if (path === '/admin/tasks' && req.method === 'GET') { await requireAdmin(req, env); return json(await listAdminTasks(env, url)); }
  if (path === '/admin/logs' && req.method === 'GET') { await requireAdmin(req, env); return json(await listQuery(env, `SELECT l.*, a.name AS agent_name, a.role AS agent_role FROM activity_log l LEFT JOIN agent a ON a.id=l.agent_id ORDER BY l.created_at DESC`, [], url)); }
  if (path === '/admin/scores/leaderboard' && req.method === 'GET') { await requireAdmin(req, env); return json(await listQuery(env, `SELECT row_number() OVER (ORDER BY total_score DESC) AS rank, id AS agent_id, name AS agent_name, role, status, total_score, created_at FROM agent ORDER BY total_score DESC`, [], url)); }

  if (path === '/agents/register' && req.method === 'POST') {
    const reg = req.headers.get('x-registration-token');
    if (reg !== registrationToken(env)) return json({ detail: '注册令牌无效' }, 403);
    reqBody = await bodyJson(req);
    const id = uid(); const apiKey = uid('ak_');
    await env.DB.prepare("INSERT INTO agent (id,name,role,description,status,api_key,total_score,created_at) VALUES (?,?,?,?,?,?,0,?)")
      .bind(id, reqBody.name, reqBody.role, reqBody.description || '', 'active', apiKey, nowIso()).run();
    return json({ id, name: reqBody.name, role: reqBody.role, api_key: apiKey, message: '注册成功，请保存 API Key' });
  }
  if (path === '/agents/me/skill' && req.method === 'GET') {
    agent = await requireAgent(req, env);
    return text(`# OpenMOSS ${agent.role} Skill\n\nBASE_URL=${url.origin}\nAPI_KEY=${agent.api_key}\n\nUse this Cloudflare deployment as your OpenMOSS endpoint.`, 200);
  }

  let agentStatus = path.match(/^\/agents\/([^/]+)\/status$/);
  if (agentStatus && req.method === 'PUT') { await requireAdmin(req, env); reqBody=await bodyJson(req); await env.DB.prepare("UPDATE agent SET status=? WHERE id=?").bind(reqBody.status||'active', agentStatus[1]).run(); return json(await env.DB.prepare("SELECT id,name,role,description,status,total_score,created_at FROM agent WHERE id=?").bind(agentStatus[1]).first()); }

  if (path === '/agents' && req.method === 'GET') { agent = await requireAgent(req, env); return json(await listQuery(env, `SELECT id,name,role,description,status,total_score,created_at FROM agent ORDER BY created_at DESC`, [], url)); }
  if (path === '/agents' && req.method === 'POST') { await requireAdmin(req, env); reqBody = await bodyJson(req); const id=uid(), apiKey=uid('ak_'); await env.DB.prepare("INSERT INTO agent (id,name,role,description,status,api_key,total_score,created_at) VALUES (?,?,?,?,?,?,0,?)").bind(id, reqBody.name, reqBody.role, reqBody.description||'', 'active', apiKey, nowIso()).run(); return json({ id, name:reqBody.name, role:reqBody.role, api_key:apiKey, message:'注册成功，请保存 API Key' }); }

  if (path === '/tasks' && req.method === 'POST') { agent = await requireAgent(req, env); requireRole(agent, 'planner'); reqBody = await bodyJson(req); const id=uid(); const t=nowIso(); await env.DB.prepare("INSERT INTO task (id,name,description,type,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)").bind(id, reqBody.name, reqBody.description||'', reqBody.type||'once', 'planning', t, t).run(); return json(await env.DB.prepare("SELECT * FROM task WHERE id=?").bind(id).first()); }
  if (path === '/tasks' && req.method === 'GET') { agent = await requireAgent(req, env); const status=url.searchParams.get('status'); return json(await listQuery(env, `SELECT * FROM task ${status?'WHERE status=?':''} ORDER BY created_at DESC`, status?[status]:[], url)); }
  let m = path.match(/^\/tasks\/([^/]+)$/);
  if (m && req.method === 'GET') { agent = await requireAgent(req, env); const row=await env.DB.prepare("SELECT * FROM task WHERE id=?").bind(m[1]).first(); return row?json(row):json({detail:'任务不存在'},404); }
  if (m && req.method === 'PUT') { agent = await requireAgent(req, env); requireRole(agent,'planner'); reqBody=await bodyJson(req); await env.DB.prepare("UPDATE task SET name=COALESCE(?,name), description=COALESCE(?,description), updated_at=? WHERE id=?").bind(reqBody.name??null, reqBody.description??null, nowIso(), m[1]).run(); return json(await env.DB.prepare("SELECT * FROM task WHERE id=?").bind(m[1]).first()); }
  m = path.match(/^\/tasks\/([^/]+)\/status$/);
  if (m && req.method === 'PUT') { agent=await requireAgent(req,env); requireRole(agent,'planner'); reqBody=await bodyJson(req); await env.DB.prepare("UPDATE task SET status=?, updated_at=? WHERE id=?").bind(reqBody.status, nowIso(), m[1]).run(); return json(await env.DB.prepare("SELECT * FROM task WHERE id=?").bind(m[1]).first()); }
  m = path.match(/^\/tasks\/([^/]+)\/modules$/);
  if (m && req.method === 'POST') { agent=await requireAgent(req,env); requireRole(agent,'planner'); reqBody=await bodyJson(req); const id=uid(); await env.DB.prepare("INSERT INTO module (id,task_id,name,description,created_at) VALUES (?,?,?,?,?)").bind(id,m[1],reqBody.name,reqBody.description||'',nowIso()).run(); return json(await env.DB.prepare("SELECT * FROM module WHERE id=?").bind(id).first()); }
  if (m && req.method === 'GET') { agent=await requireAgent(req,env); return json((await env.DB.prepare("SELECT * FROM module WHERE task_id=? ORDER BY created_at DESC").bind(m[1]).all()).results||[]); }

  if (path === '/sub-tasks' && req.method === 'POST') { agent=await requireAgent(req,env); requireRole(agent,'planner'); reqBody=await bodyJson(req); const id=uid(); const t=nowIso(); await env.DB.prepare(`INSERT INTO sub_task (id,task_id,module_id,name,description,deliverable,acceptance,type,status,priority,assigned_agent,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(id,reqBody.task_id,reqBody.module_id||null,reqBody.name,reqBody.description||'',reqBody.deliverable||'',reqBody.acceptance||'',reqBody.type||'once','pending',reqBody.priority||'medium',reqBody.assigned_agent||null,t,t).run(); return json(await env.DB.prepare("SELECT * FROM sub_task WHERE id=?").bind(id).first()); }
  if (path === '/sub-tasks' && req.method === 'GET') { agent=await requireAgent(req,env); const filters=[]; const binds=[]; for (const k of ['task_id','module_id','status']) { const v=url.searchParams.get(k); if(v){filters.push(`${k}=?`); binds.push(v);} } return json(await listQuery(env, `SELECT * FROM sub_task ${filters.length?'WHERE '+filters.join(' AND '):''} ORDER BY created_at DESC`, binds, url)); }
  if (path === '/sub-tasks/mine' && req.method === 'GET') { agent=await requireAgent(req,env); const status=url.searchParams.get('status'); const binds=[agent.id]; let where='assigned_agent=?'; if(status){where+=' AND status=?'; binds.push(status);} return json(await listQuery(env, `SELECT * FROM sub_task WHERE ${where} ORDER BY updated_at DESC`, binds, url)); }
  if (path === '/sub-tasks/available' && req.method === 'GET') { agent=await requireAgent(req,env); return json(await listQuery(env, `SELECT * FROM sub_task WHERE status='pending' ORDER BY created_at DESC`, [], url)); }

  if (path === '/sub-tasks/latest' && req.method === 'GET') { agent=await requireAgent(req,env); const row=await env.DB.prepare("SELECT * FROM sub_task ORDER BY created_at DESC LIMIT 1").first(); return row?json(row):json({detail:'No sub tasks'},404); }

  m = path.match(/^\/sub-tasks\/([^/]+)$/);
  if (m && req.method === 'GET') { agent=await requireAgent(req,env); const row=await env.DB.prepare("SELECT * FROM sub_task WHERE id=?").bind(m[1]).first(); return row?json(row):json({detail:'子任务不存在'},404); }
  m = path.match(/^\/sub-tasks\/([^/]+)\/(claim|start|submit|complete|rework|block|reassign|cancel|session)$/);
  if (m && req.method === 'POST') { agent=await requireAgent(req,env); reqBody=await bodyJson(req); return json(await mutateSubTask(env, agent, m[1], m[2], reqBody)); }

  if (path === '/review-records' && req.method === 'POST') { agent=await requireAgent(req,env); requireRole(agent,'reviewer'); reqBody=await bodyJson(req); const row=await createReview(env, agent, reqBody); return json(row); }
  if (path === '/review-records' && req.method === 'GET') { agent=await requireAgent(req,env); const st=url.searchParams.get('sub_task_id'); return json(await listQuery(env, `SELECT * FROM review_record ${st?'WHERE sub_task_id=?':''} ORDER BY created_at DESC`, st?[st]:[], url)); }

  if (path === '/logs' && req.method === 'POST') { agent=await requireAgent(req,env); reqBody=await bodyJson(req); const id=uid(); await env.DB.prepare("INSERT INTO activity_log (id,agent_id,sub_task_id,action,summary,session_id,created_at) VALUES (?,?,?,?,?,?,?)").bind(id,agent.id,reqBody.sub_task_id||null,reqBody.action,reqBody.summary||'',reqBody.session_id||null,nowIso()).run(); return json(await env.DB.prepare("SELECT * FROM activity_log WHERE id=?").bind(id).first()); }
  if (path === '/logs' && req.method === 'GET') { agent=await requireAgent(req,env); return json(await listQuery(env, `SELECT * FROM activity_log ORDER BY created_at DESC`, [], url)); }
  if (path === '/logs/mine' && req.method === 'GET') { agent=await requireAgent(req,env); return json(await listQuery(env, `SELECT * FROM activity_log WHERE agent_id=? ORDER BY created_at DESC`, [agent.id], url)); }

  if (path === '/scores/leaderboard' && req.method === 'GET') { agent=await requireAgent(req,env); return json((await env.DB.prepare(`SELECT row_number() OVER (ORDER BY total_score DESC) AS rank, id AS agent_id, name AS agent_name, role, total_score FROM agent ORDER BY total_score DESC`).all()).results||[]); }
  if (path === '/scores/me' && req.method === 'GET') { agent=await requireAgent(req,env); return json(await scoreSummary(env, agent.id)); }

  let scoreOne = path.match(/^\/scores\/([^/]+)$/);
  if (scoreOne && req.method === 'GET') { agent=await requireAgent(req,env); return json(await scoreSummary(env, scoreOne[1])); }
  if (path === '/scores/me/logs' && req.method === 'GET') { agent=await requireAgent(req,env); return json((await env.DB.prepare("SELECT * FROM reward_log WHERE agent_id=? ORDER BY created_at DESC").bind(agent.id).all()).results||[]); }
  let scoreLogs = path.match(/^\/scores\/([^/]+)\/logs$/);
  if (scoreLogs && req.method === 'GET') { agent=await requireAgent(req,env); return json((await env.DB.prepare("SELECT * FROM reward_log WHERE agent_id=? ORDER BY created_at DESC").bind(scoreLogs[1]).all()).results||[]); }
  if (path === '/scores/adjust' && req.method === 'POST') { agent=await requireAgent(req,env); reqBody=await bodyJson(req); const id=uid(); await env.DB.prepare("INSERT INTO reward_log (id,agent_id,sub_task_id,reason,score_delta,created_at) VALUES (?,?,?,?,?,?)").bind(id,reqBody.agent_id||agent.id,reqBody.sub_task_id||null,reqBody.reason||'manual',Number(reqBody.score_delta||0),nowIso()).run(); await env.DB.prepare("UPDATE agent SET total_score=total_score+? WHERE id=?").bind(Number(reqBody.score_delta||0),reqBody.agent_id||agent.id).run(); return json(await env.DB.prepare("SELECT * FROM reward_log WHERE id=?").bind(id).first()); }

  if (path === '/feed/status') return json({ enabled: publicFeed(env) });
  if (path === '/feed/agent-summary') { if(!publicFeed(env)) return json({detail:'活动流展示页未启用'},403); return json((await env.DB.prepare("SELECT id AS agent_id, name AS agent_name, role, status, total_score FROM agent ORDER BY total_score DESC").all()).results||[]); }
  if (path === '/feed/agents') { if(!publicFeed(env)) return json({detail:'活动流展示页未启用'},403); return json((await env.DB.prepare("SELECT id,name,role,status,total_score,created_at FROM agent ORDER BY total_score DESC").all()).results||[]); }
  if (path === '/feed/logs') { if(!publicFeed(env)) return json({detail:'活动流展示页未启用'},403); return json(await listQuery(env, `SELECT * FROM request_log ORDER BY timestamp DESC`, [], url)); }
  if (path === '/tools/cli') { agent=await requireAgent(req,env); return text(`# Minimal OpenMOSS Cloudflare CLI endpoint\nBASE_URL = "${url.origin}"\nAPI_KEY = "${agent.api_key}"\n`); }

  return json({ detail: 'Not Found', path }, 404);
}

async function mutateSubTask(env, agent, id, op, body) {
  const st = await env.DB.prepare("SELECT * FROM sub_task WHERE id=?").bind(id).first();
  if (!st) throw Object.assign(new Error('子任务不存在'), {status:404});
  const t=nowIso();
  if (op === 'claim') await env.DB.prepare("UPDATE sub_task SET status='assigned', assigned_agent=?, current_session_id=?, updated_at=? WHERE id=?").bind(agent.id, body.session_id||null, t, id).run();
  if (op === 'start') await env.DB.prepare("UPDATE sub_task SET status='in_progress', current_session_id=?, updated_at=? WHERE id=?").bind(body.session_id||null, t, id).run();
  if (op === 'submit') await env.DB.prepare("UPDATE sub_task SET status='review', deliverable=COALESCE(?,deliverable), updated_at=? WHERE id=?").bind(body.deliverable||body.summary||null, t, id).run();
  if (op === 'complete') await env.DB.prepare("UPDATE sub_task SET status='done', completed_at=?, updated_at=? WHERE id=?").bind(t, t, id).run();
  if (op === 'cancel') await env.DB.prepare("UPDATE sub_task SET status='cancelled', updated_at=? WHERE id=?").bind(t, id).run();
  if (op === 'block') await env.DB.prepare("UPDATE sub_task SET status='blocked', updated_at=? WHERE id=?").bind(t, id).run();
  if (op === 'rework') await env.DB.prepare("UPDATE sub_task SET status='rework', assigned_agent=COALESCE(?,assigned_agent), rework_count=rework_count+1, updated_at=? WHERE id=?").bind(body.rework_agent||body.assigned_agent||null, t, id).run();
  if (op === 'reassign') await env.DB.prepare("UPDATE sub_task SET assigned_agent=?, status='assigned', updated_at=? WHERE id=?").bind(body.assigned_agent||body.agent_id||null, t, id).run();
  if (op === 'session') await env.DB.prepare("UPDATE sub_task SET current_session_id=?, updated_at=? WHERE id=?").bind(body.session_id||null, t, id).run();
  await env.DB.prepare("INSERT INTO activity_log (id,agent_id,sub_task_id,action,summary,session_id,created_at) VALUES (?,?,?,?,?,?,?)").bind(uid(),agent.id,id,op,body.summary||`${op} sub task`,body.session_id||null,t).run();
  return await env.DB.prepare("SELECT * FROM sub_task WHERE id=?").bind(id).first();
}

async function createReview(env, agent, b) {
  const last = await env.DB.prepare("SELECT max(round) AS r FROM review_record WHERE sub_task_id=?").bind(b.sub_task_id).first();
  const round = (last?.r || 0) + 1; const id=uid(); const t=nowIso();
  await env.DB.prepare("INSERT INTO review_record (id,sub_task_id,reviewer_agent,round,result,score,issues,comment,rework_agent,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)").bind(id,b.sub_task_id,agent.id,round,b.result,b.score,b.issues||'',b.comment||'',b.rework_agent||null,t).run();
  if (b.result === 'approved') await env.DB.prepare("UPDATE sub_task SET status='done', completed_at=?, updated_at=? WHERE id=?").bind(t,t,b.sub_task_id).run();
  else await env.DB.prepare("UPDATE sub_task SET status='rework', rework_count=rework_count+1, assigned_agent=COALESCE(?,assigned_agent), updated_at=? WHERE id=?").bind(b.rework_agent||null,t,b.sub_task_id).run();
  await env.DB.prepare("UPDATE agent SET total_score=total_score+? WHERE id=(SELECT assigned_agent FROM sub_task WHERE id=?)").bind(Number(b.score||0), b.sub_task_id).run();
  return await env.DB.prepare("SELECT * FROM review_record WHERE id=?").bind(id).first();
}
async function scoreSummary(env, agentId) {
  const a=await env.DB.prepare("SELECT *, (SELECT count(*) FROM agent) AS total_agents FROM agent WHERE id=?").bind(agentId).first();
  if(!a) return null;
  const rank=await env.DB.prepare("SELECT count(*)+1 AS rank FROM agent WHERE total_score > ?").bind(a.total_score).first();
  const counts=await env.DB.prepare("SELECT count(*) AS total_records, sum(case when score_delta>0 then 1 else 0 end) AS reward_count, sum(case when score_delta<0 then 1 else 0 end) AS penalty_count FROM reward_log WHERE agent_id=?").bind(agentId).first();
  return {agent_id:a.id, agent_name:a.name, total_score:a.total_score, rank:rank.rank, total_agents:a.total_agents, reward_count:counts.reward_count||0, penalty_count:counts.penalty_count||0, total_records:counts.total_records||0};
}
async function dashboardOverview(env) {
  const one = async sql => (await env.DB.prepare(sql).first())?.c || 0;
  const dist = async (table,col,vals) => { const rows=(await env.DB.prepare(`SELECT ${col} v,count(*) c FROM ${table} GROUP BY ${col}`).all()).results||[]; const out=Object.fromEntries(vals.map(v=>[v,0])); for(const r of rows) if(r.v in out) out[r.v]=r.c; return out; };
  const taskD=await dist('task','status',['planning','active','in_progress','completed','archived','cancelled']);
  const subD=await dist('sub_task','status',['pending','assigned','in_progress','review','rework','blocked','done','cancelled']);
  const agentD=await dist('agent','status',['active','disabled']);
  const roleD=await dist('agent','role',['planner','executor','reviewer','patrol']);
  return { generated_at: nowIso(), core_cards:{ open_task_count:taskD.planning+taskD.active+taskD.in_progress, active_sub_task_count:subD.assigned+subD.in_progress+subD.review+subD.rework+subD.blocked, review_queue_count:subD.review, blocked_sub_task_count:subD.blocked, active_agent_count:agentD.active, today_completed_sub_task_count:0 }, secondary_cards:{ disabled_agent_count:agentD.disabled, today_review_count:0, today_rejected_review_count:0, today_reject_rate:0, today_net_score_delta:0 }, distributions:{ task_status_distribution:taskD, sub_task_status_distribution:subD, agent_status_distribution:agentD, agent_role_distribution:roleD, review_result_distribution_7d:{approved:0,rejected:0} } };
}
async function listAdminAgents(env,url){
  const rows=(await env.DB.prepare(`SELECT a.id,a.name,a.role,a.description,a.status,a.total_score,a.created_at,
    0 AS rank,
    (SELECT count(*) FROM sub_task s WHERE s.assigned_agent=a.id AND s.status NOT IN ('done','cancelled')) AS open_sub_task_count,
    (SELECT count(*) FROM sub_task s WHERE s.assigned_agent=a.id AND s.status='assigned') AS assigned_count,
    (SELECT count(*) FROM sub_task s WHERE s.assigned_agent=a.id AND s.status='in_progress') AS in_progress_count,
    (SELECT count(*) FROM sub_task s WHERE s.assigned_agent=a.id AND s.status='review') AS review_count,
    (SELECT count(*) FROM sub_task s WHERE s.assigned_agent=a.id AND s.status='rework') AS rework_count,
    (SELECT count(*) FROM sub_task s WHERE s.assigned_agent=a.id AND s.status='blocked') AS blocked_count,
    (SELECT max(timestamp) FROM request_log l WHERE l.agent_id=a.id) AS last_request_at,
    (SELECT max(created_at) FROM activity_log l WHERE l.agent_id=a.id) AS last_activity_at
    FROM agent a ORDER BY total_score DESC, created_at DESC`).all()).results||[];
  rows.forEach((r,i)=>r.rank=i+1);
  return page(rows,url);
}
async function listAdminTasks(env,url){
  const rows=(await env.DB.prepare(`SELECT t.*,
    (SELECT count(*) FROM module m WHERE m.task_id=t.id) AS module_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id) AS sub_task_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id AND s.status='pending') AS pending_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id AND s.status='assigned') AS assigned_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id AND s.status='in_progress') AS in_progress_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id AND s.status='review') AS review_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id AND s.status='rework') AS rework_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id AND s.status='blocked') AS blocked_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id AND s.status='done') AS done_count,
    (SELECT count(*) FROM sub_task s WHERE s.task_id=t.id AND s.status='cancelled') AS cancelled_count
    FROM task t ORDER BY created_at DESC`).all()).results||[];
  return page(rows,url);
}

const INDEX_HTML = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>OpenMOSS Cloudflare</title><style>
body{margin:0;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#07111f;color:#e5f0ff} .wrap{max-width:1180px;margin:0 auto;padding:32px 20px} .hero{padding:28px;border:1px solid #23334d;border-radius:22px;background:linear-gradient(135deg,#13284a,#0b1728 55%,#10251e);box-shadow:0 20px 70px #0008}.title{font-size:42px;font-weight:900;margin:0}.sub{color:#9fb3d1}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-top:18px}.card{background:#0d1a2d;border:1px solid #20324f;border-radius:18px;padding:18px}.num{font-size:32px;font-weight:900}.muted{color:#8ea3c3}.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}button,input,select,textarea{border-radius:12px;border:1px solid #2b4164;background:#0b1525;color:#e5f0ff;padding:10px 12px}button{cursor:pointer;background:#2563eb;border-color:#3b82f6;font-weight:700}.ok{color:#34d399}.bad{color:#fb7185}pre{white-space:pre-wrap;background:#030712;border:1px solid #1f2937;border-radius:14px;padding:14px;max-height:420px;overflow:auto}a{color:#60a5fa}.pill{display:inline-flex;gap:6px;padding:5px 10px;border-radius:999px;background:#11233d;border:1px solid #29466f;color:#bfdbfe;font-size:12px}</style></head><body><div class="wrap"><section class="hero"><div class="pill">Cloudflare Workers + Pages-style UI + D1</div><h1 class="title">OpenMOSS Cloudflare</h1><p class="sub">OpenMOSS 多 Agent 协作中间件的 Cloudflare 原生实现：Worker API、D1 数据库、单页管理界面。</p><div class="row"><button onclick="loadHealth()">健康检查</button><button onclick="loadDashboard()">刷新仪表盘</button><button onclick="loadFeed()">公开活动流</button><a href="/api/health" target="_blank">/api/health</a></div></section><div class="grid" id="cards"></div><section class="card" style="margin-top:18px"><h2>Admin Login</h2><div class="row"><input id="pwd" type="password" placeholder="Admin password"><button onclick="login()">登录</button><button onclick="loadAdmin()">加载管理数据</button></div><p class="muted">登录后 token 保存在浏览器 localStorage。</p></section><section class="card" style="margin-top:18px"><h2>Agent 注册</h2><div class="row"><input id="regToken" placeholder="registration token"><input id="agentName" placeholder="agent name"><select id="agentRole"><option>planner</option><option>executor</option><option>reviewer</option><option>patrol</option></select><button onclick="registerAgent()">注册</button></div></section><section class="card" style="margin-top:18px"><h2>输出</h2><pre id="out">Ready.</pre></section></div><script>
const out=x=>document.getElementById('out').textContent=typeof x==='string'?x:JSON.stringify(x,null,2); const api=(p,o={})=>fetch('/api'+p,o).then(r=>r.json());
async function loadHealth(){out(await api('/health'))} async function loadDashboard(){const d=await api('/admin/dashboard/overview',{headers:{'x-admin-token':localStorage.mossAdmin||''}}); renderCards(d); out(d)}
function renderCards(d){const c=d.core_cards||{}; document.getElementById('cards').innerHTML=[['开放任务',c.open_task_count],['活跃子任务',c.active_sub_task_count],['待审查',c.review_queue_count],['阻塞',c.blocked_sub_task_count],['活跃 Agent',c.active_agent_count],['今日完成',c.today_completed_sub_task_count]].map(([k,v])=>'<div class="card"><div class="muted">'+k+'</div><div class="num">'+(v??'-')+'</div></div>').join('')}
async function login(){const r=await api('/admin/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({password:document.getElementById('pwd').value})}); if(r.token)localStorage.mossAdmin=r.token; out(r)}
async function loadAdmin(){const h={'x-admin-token':localStorage.mossAdmin||''}; const data={config:await api('/admin/config',{headers:h}),agents:await api('/admin/agents?page_size=20',{headers:h}),tasks:await api('/admin/tasks?page_size=20',{headers:h})}; out(data)}
async function loadFeed(){out({status:await api('/feed/status'), agents:await api('/feed/agents'), logs:await api('/feed/logs?limit=20')})}
async function registerAgent(){const r=await api('/agents/register',{method:'POST',headers:{'content-type':'application/json','x-registration-token':document.getElementById('regToken').value},body:JSON.stringify({name:document.getElementById('agentName').value,role:document.getElementById('agentRole').value,description:'Registered from Cloudflare UI'})}); out(r)}
loadHealth();
</script></body></html>`;

const SCHEMA_SQL = `-- OpenMOSS Cloudflare D1 schema
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
`;

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    try {
      if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: JSON_HEADERS });
      if (url.pathname === '/__init' && req.method === 'POST') { await initSchema(env); return json({ ok: true, message: 'schema initialized' }); }
      if (url.pathname.startsWith('/api/')) return await routeApi(req, env, ctx);
      if (url.pathname === '/' || !url.pathname.includes('.')) return html(INDEX_HTML);
      return text('Not found', 404);
    } catch (e) {
      console.log('error', e.stack || e.message);
      return json({ detail: e.message || 'Internal Error' }, e.status || 500);
    }
  }
};
