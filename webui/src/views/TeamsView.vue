<template>
  <div class="teams-view">
    <header class="page-header">
      <h1>团队空间</h1>
      <div class="header-actions">
        <Button @click="showCreateModal = true">
          <Plus class="w-4 h-4 mr-2" />
          创建团队
        </Button>
        <Button variant="outline" @click="showTemplateModal = true">
          <FileText class="w-4 h-4 mr-2" />
          团队介绍模板
        </Button>
      </div>
    </header>

    <!-- 团队列表 -->
    <div class="teams-table">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>团队名称</TableHead>
            <TableHead>描述</TableHead>
            <TableHead>工作目录</TableHead>
            <TableHead>成员数</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="team in teams" :key="team.id">
            <TableCell class="font-medium">{{ team.name }}</TableCell>
            <TableCell class="text-muted-foreground">{{ team.description || '-' }}</TableCell>
            <TableCell class="text-muted-foreground font-mono text-xs">{{ team.working_dir || '-' }}</TableCell>
            <TableCell>{{ team.member_count }}</TableCell>
            <TableCell>
              <Badge :variant="team.status === 'active' ? 'default' : 'secondary'">
                {{ team.status === 'active' ? '启用' : '禁用' }}
              </Badge>
            </TableCell>
            <TableCell>
              <div class="flex gap-2">
                <Button variant="ghost" size="sm" @click="viewTeam(team)">
                  查看
                </Button>
                <Button variant="ghost" size="sm" @click="editTeam(team)">
                  编辑
                </Button>
              </div>
            </TableCell>
          </TableRow>
          <TableRow v-if="teams.length === 0">
            <TableCell colspan="6" class="text-center text-muted-foreground py-8">
              暂无团队，点击上方按钮创建
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <!-- 团队详情侧边栏 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showDetailSheet" class="fixed inset-0 z-40">
          <div class="absolute inset-0 bg-black/20" @click="showDetailSheet = false" />
          <div class="absolute right-0 top-0 h-full w-[500px] bg-background border-l p-6 overflow-y-auto">
            <div class="flex items-center justify-between mb-6">
              <div>
                <h2 class="text-xl font-semibold">{{ selectedTeam?.name }}</h2>
                <p class="text-sm text-muted-foreground">{{ selectedTeam?.description || '暂无描述' }}</p>
                <p class="text-xs text-muted-foreground font-mono mt-1">{{ selectedTeam?.working_dir || '未设置工作目录' }}</p>
              </div>
              <Button variant="ghost" size="icon" @click="showDetailSheet = false">
                <X class="w-5 h-5" />
              </Button>
            </div>

            <!-- 成员列表 -->
            <div class="mb-6">
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-sm font-medium">团队成员 ({{ selectedTeam?.members?.length || 0 }})</h3>
                <Button variant="outline" size="sm" @click="showAddMemberModal = true">
                  <Plus class="w-4 h-4 mr-1" />
                  添加成员
                </Button>
              </div>
              <div class="space-y-2">
                <div
                  v-for="member in selectedTeam?.members"
                  :key="member.id"
                  class="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div>
                    <div class="font-medium">{{ member.agent_name }}</div>
                    <div class="text-xs text-muted-foreground">{{ member.role }}</div>
                  </div>
                  <div class="flex items-center gap-2">
                    <Badge :variant="member.self_introduction ? 'default' : 'outline'" class="text-xs">
                      {{ member.self_introduction ? '已完成介绍' : '待完成' }}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 text-red-500 hover:text-red-600"
                      @click="removeMember(member.agent_id)"
                    >
                      <Trash2 class="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                <div v-if="!selectedTeam?.members?.length" class="text-center text-muted-foreground py-4 text-sm">
                  暂无成员
                </div>
              </div>
            </div>

            <!-- 团队介绍预览 -->
            <div>
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-sm font-medium">团队介绍预览</h3>
                <div class="flex gap-2">
                  <Button variant="outline" size="sm" @click="openEditProfile">
                    <Pencil class="w-4 h-4 mr-1" />
                    编辑
                  </Button>
                  <Button variant="outline" size="sm" @click="refreshProfile">
                    <RefreshCw class="w-4 h-4 mr-1" />
                    刷新
                  </Button>
                </div>
              </div>
              <div class="p-4 rounded-lg bg-muted max-h-[400px] overflow-y-auto">
                <pre class="text-sm whitespace-pre-wrap font-mono">{{ teamProfile || '暂无内容' }}</pre>
              </div>
            </div>

            <!-- 知识经验区域 -->
            <div class="space-y-4 pt-4 border-t">
              <div class="flex justify-between items-center">
                <h2 class="text-lg font-semibold">知识经验</h2>
                <div class="flex gap-2">
                  <Input
                    v-model="knowledgeSearchQuery"
                    placeholder="搜索知识..."
                    class="w-48"
                    @keyup.enter="searchKnowledge"
                  />
                  <Button variant="outline" size="sm" @click="searchKnowledge">搜索</Button>
                  <Button size="sm" @click="knowledgeMode = 'upload'; showKnowledgeSheet = true">
                    上传知识
                  </Button>
                </div>
              </div>

              <!-- 搜索结果 -->
              <div v-if="knowledgeMode === 'search'" class="space-y-2">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">搜索结果 ({{ knowledgeSearchTotal }})</span>
                  <Button variant="ghost" size="sm" @click="knowledgeMode = 'list'">返回列表</Button>
                </div>
                <Card
                  v-for="item in knowledgeSearchResults"
                  :key="item.id"
                  class="cursor-pointer hover:bg-accent"
                  @click="viewKnowledge(item)"
                >
                  <CardHeader class="py-3">
                    <CardTitle class="text-sm">{{ item.title }}</CardTitle>
                    <CardDescription>来自: {{ item.team_name }}</CardDescription>
                  </CardHeader>
                </Card>
              </div>

              <!-- 本团队知识列表 -->
              <div v-if="knowledgeMode === 'list'" class="space-y-2">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">本团队 ({{ knowledgeTotal }})</span>
                </div>
                <Card
                  v-for="item in knowledgeList"
                  :key="item.id"
                  class="cursor-pointer hover:bg-accent"
                  @click="viewKnowledge(item)"
                >
                  <CardHeader class="py-3">
                    <CardTitle class="text-sm">{{ item.title }}</CardTitle>
                    <CardDescription>作者: {{ item.author_agent_id }}</CardDescription>
                  </CardHeader>
                </Card>
                <div v-if="knowledgeList.length === 0" class="text-center text-muted-foreground py-4">
                  暂无知识经验
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 创建团队弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40" @click="showCreateModal = false" />
          <div class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-lg">
            <h2 class="text-lg font-semibold mb-4">创建团队</h2>
            <form @submit.prevent="createTeam" class="space-y-4">
              <div>
                <Label>团队名称</Label>
                <Input v-model="newTeam.name" placeholder="请输入团队名称" required />
              </div>
              <div>
                <Label>团队描述</Label>
                <textarea v-model="newTeam.description" placeholder="请输入团队描述（可选）" class="w-full min-h-[80px] px-3 py-2 rounded-md border bg-background" />
              </div>
              <div>
                <Label>工作目录</Label>
                <Input v-model="newTeam.working_dir" placeholder="例如: /workspace/teams/my-team" required />
              </div>
              <div class="flex justify-end gap-3">
                <Button type="button" variant="outline" @click="showCreateModal = false">取消</Button>
                <Button type="submit">创建</Button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 编辑团队弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showEditModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40" @click="showEditModal = false" />
          <div class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-lg">
            <h2 class="text-lg font-semibold mb-4">编辑团队</h2>
            <form @submit.prevent="saveTeam" class="space-y-4">
              <div>
                <Label>团队名称</Label>
                <Input v-model="editData.name" required />
              </div>
              <div>
                <Label>团队描述</Label>
                <textarea v-model="editData.description" class="w-full min-h-[80px] px-3 py-2 rounded-md border bg-background" />
              </div>
              <div>
                <Label>工作目录</Label>
                <Input :model-value="editData.working_dir" disabled class="bg-muted" />
              </div>
              <div>
                <Label>状态</Label>
                <select v-model="editData.status" class="w-full px-3 py-2 rounded-md border bg-background">
                  <option value="active">启用</option>
                  <option value="disabled">禁用</option>
                </select>
              </div>
              <div class="flex justify-end gap-3">
                <Button type="button" variant="outline" @click="showEditModal = false">取消</Button>
                <Button type="submit">保存</Button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 添加成员弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showAddMemberModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40" @click="showAddMemberModal = false" />
          <div class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-lg">
            <h2 class="text-lg font-semibold mb-4">添加成员</h2>
            <div class="space-y-4">
              <div>
                <Label>选择 Agent</Label>
                <select v-model="newMember.agentId" class="w-full px-3 py-2 rounded-md border bg-background">
                  <option value="">选择 Agent</option>
                  <option
                    v-for="agent in agentsWithTeamInfo"
                    :key="agent.id"
                    :value="agent.id"
                    :disabled="agent.hasTeam"
                    :class="{ 'text-muted-foreground': agent.hasTeam }"
                  >
                    {{ agent.name }} ({{ agent.role }})
                    <template v-if="agent.hasTeam">
                      - 已加入: {{ agent.teamName }}
                    </template>
                  </option>
                </select>
                <p v-if="agentsWithTeamInfo.some(a => a.hasTeam)" class="text-xs text-muted-foreground mt-1">
                  灰色选项表示该 Agent 已加入其他团队
                </p>
              </div>
              <div class="flex justify-end gap-3">
                <Button type="button" variant="outline" @click="showAddMemberModal = false">取消</Button>
                <Button @click="addMember">添加</Button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 模板编辑弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showTemplateModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40" @click="showTemplateModal = false" />
          <div class="relative z-10 w-full max-w-2xl rounded-xl border bg-background p-6 shadow-lg">
            <h2 class="text-lg font-semibold mb-2">团队介绍生成模板</h2>
            <p class="text-sm text-muted-foreground mb-4">
              支持变量: {'{'}team_name{'}'}, {'{'}team_description{'}'}, {'{'}members{'}'}
            </p>
            <textarea v-model="templateContent" rows="15" class="w-full font-mono" />
            <div class="flex justify-end gap-3 mt-4">
              <Button type="button" variant="outline" @click="showTemplateModal = false">取消</Button>
              <Button @click="saveTemplate">保存</Button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 编辑团队介绍弹窗 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showEditProfileModal" class="fixed inset-0 z-50 flex items-center justify-center">
          <div class="absolute inset-0 bg-black/40" @click="showEditProfileModal = false" />
          <div class="relative z-10 w-full max-w-2xl rounded-xl border bg-background p-6 shadow-lg">
            <h2 class="text-lg font-semibold mb-2">编辑团队介绍</h2>
            <p class="text-sm text-muted-foreground mb-4">
              您可以直接编辑团队介绍内容
            </p>
            <textarea v-model="editProfileContent" rows="20" class="w-full font-mono" />
            <div class="flex justify-end gap-3 mt-4">
              <Button type="button" variant="outline" @click="showEditProfileModal = false">取消</Button>
              <Button @click="saveProfile">保存</Button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 知识详情/上传侧边栏 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showKnowledgeSheet" class="fixed inset-0 z-40">
          <div class="absolute inset-0 bg-black/20" @click="showKnowledgeSheet = false" />
          <div class="absolute right-0 top-0 h-full w-96 bg-background border-l p-6 overflow-y-auto">
            <!-- 上传模式 -->
            <div v-if="knowledgeMode === 'upload'">
              <h2 class="text-lg font-semibold mb-4">上传知识</h2>
              <div class="space-y-4">
                <div>
                  <Label>标题</Label>
                  <Input v-model="knowledgeForm.title" placeholder="输入标题" />
                </div>
                <div>
                  <Label>内容</Label>
                  <Input v-model="knowledgeForm.content" type="textarea" rows="10" placeholder="输入内容" />
                </div>
                <Button class="w-full" @click="uploadKnowledge">上传</Button>
              </div>
            </div>

            <!-- 查看模式 -->
            <div v-else-if="selectedKnowledge">
              <div class="flex justify-between items-start mb-4">
                <h2 class="text-lg font-semibold">知识详情</h2>
                <Button variant="ghost" size="icon" @click="showKnowledgeSheet = false">
                  <X class="h-4 w-4" />
                </Button>
              </div>
              <div class="space-y-4">
                <div>
                  <Label>标题</Label>
                  <p class="text-sm">{{ selectedKnowledge.title }}</p>
                </div>
                <div>
                  <Label>团队</Label>
                  <p class="text-sm">{{ selectedKnowledge.team_name || selectedKnowledge.team_id }}</p>
                </div>
                <div>
                  <Label>作者</Label>
                  <p class="text-sm">{{ selectedKnowledge.author_agent_id }}</p>
                </div>
                <div>
                  <Label>内容</Label>
                  <p class="text-sm whitespace-pre-wrap">{{ selectedKnowledge.content }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Plus, FileText, Trash2, RefreshCw, X, Pencil } from 'lucide-vue-next'
import { adminTeamApi, adminAgentApi, knowledgeApi } from '@/api/client'
import { toast } from 'vue-sonner'

// 数据
const teams = ref<any[]>([])
const selectedTeam = ref<any>(null)
const teamProfile = ref('')
const showDetailSheet = ref(false)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showAddMemberModal = ref(false)
const showTemplateModal = ref(false)
const showEditProfileModal = ref(false)

const newTeam = ref({ name: '', description: '', working_dir: '' })
const editData = ref({ name: '', description: '', status: 'active', working_dir: '' })
const newMember = ref({ agentId: '' })
const availableAgents = ref<any[]>([])
const teamMembers = ref<any[]>([])  // 所有团队的成员信息
const templateContent = ref('')
const editProfileContent = ref('')

// 知识状态
const knowledgeList = ref<any[]>([])
const knowledgeTotal = ref(0)
const knowledgeSearchResults = ref<any[]>([])
const knowledgeSearchTotal = ref(0)
const selectedKnowledge = ref<any>(null)
const showKnowledgeSheet = ref(false)
const knowledgeForm = ref({ title: '', content: '' })
const knowledgeSearchQuery = ref('')
const knowledgeMode = ref<'list' | 'search' | 'upload'>('list')

// 计算每个 agent 的团队归属信息
const agentTeamInfo = computed(() => {
  const map: Record<string, { teamName: string; teamId: string }> = {}
  for (const member of teamMembers.value) {
    map[member.agent_id] = {
      teamName: member.team_name,
      teamId: member.team_id
    }
  }
  return map
})

// 可选 Agent 列表（包含团队信息）
const agentsWithTeamInfo = computed(() => {
  return availableAgents.value.map(agent => {
    const teamInfo = agentTeamInfo.value[agent.id]
    return {
      ...agent,
      hasTeam: !!teamInfo,
      teamName: teamInfo?.teamName || ''
    }
  })
})

// 加载团队列表
async function loadTeams() {
  try {
    const res = await adminTeamApi.list({ page: 1, page_size: 100 })
    teams.value = res.data.items
  } catch (e) {
    console.error('Failed to load teams:', e)
  }
}

// 选择团队
async function viewTeam(team: any) {
  try {
    const res = await adminTeamApi.get(team.id)
    selectedTeam.value = res.data
    showDetailSheet.value = true
    await refreshProfile()
  } catch (e) {
    console.error('Failed to load team:', e)
  }
}

// 编辑团队
function editTeam(team: any) {
  editData.value = {
    name: team.name,
    description: team.description,
    status: team.status,
    working_dir: team.working_dir || '未设置',
  }
  selectedTeam.value = team
  showEditModal.value = true
}

// 保存团队
async function saveTeam() {
  if (!selectedTeam.value) return
  try {
    await adminTeamApi.update(selectedTeam.value.id, editData.value)
    showEditModal.value = false
    await loadTeams()
    await viewTeam({ id: selectedTeam.value.id })
  } catch (e) {
    console.error('Failed to update team:', e)
  }
}

// 创建团队
async function createTeam() {
  try {
    await adminTeamApi.create(newTeam.value)
    showCreateModal.value = false
    newTeam.value = { name: '', description: '', working_dir: '' }
    await loadTeams()
  } catch (e) {
    console.error('Failed to create team:', e)
  }
}

// 刷新团队介绍预览
async function refreshProfile() {
  if (!selectedTeam.value) return
  try {
    const res = await adminTeamApi.getProfile(selectedTeam.value.id)
    teamProfile.value = res.data.content
  } catch (e) {
    console.error('Failed to load profile:', e)
    teamProfile.value = ''
  }
}

// 打开编辑团队介绍弹窗
function openEditProfile() {
  editProfileContent.value = teamProfile.value
  showEditProfileModal.value = true
}

// 保存团队介绍
async function saveProfile() {
  if (!selectedTeam.value) return
  try {
    await adminTeamApi.updateProfileContent(selectedTeam.value.id, editProfileContent.value)
    teamProfile.value = editProfileContent.value
    showEditProfileModal.value = false
    toast.success('团队介绍已更新')
  } catch (e: any) {
    console.error('Failed to save profile:', e)
    const msg = e?.response?.data?.detail || '保存失败'
    toast.error(msg)
  }
}

// 添加成员
async function addMember() {
  if (!selectedTeam.value || !newMember.value.agentId) return
  try {
    await adminTeamApi.addMember(selectedTeam.value.id, newMember.value.agentId)
    showAddMemberModal.value = false
    newMember.value = { agentId: '' }
    await viewTeam({ id: selectedTeam.value.id })
    toast.success('成员添加成功')
  } catch (e: any) {
    console.error('Failed to add member:', e)
    const msg = e?.response?.data?.detail || '添加成员失败'
    toast.error(msg)
  }
}

// 移除成员
async function removeMember(agentId: string) {
  if (!selectedTeam.value) return
  if (!confirm('确定要移除该成员吗？')) return
  try {
    await adminTeamApi.removeMember(selectedTeam.value.id, agentId)
    await viewTeam({ id: selectedTeam.value.id })
  } catch (e) {
    console.error('Failed to remove member:', e)
  }
}

// 加载可用 Agent 和团队成员信息
async function loadAvailableAgents() {
  try {
    const res = await adminAgentApi.list({ status: 'active' })
    availableAgents.value = res.data.items

    // 加载所有团队及其成员信息
    teamMembers.value = []
    for (const team of teams.value) {
      try {
        const teamRes = await adminTeamApi.get(team.id)
        const members = teamRes.data.members || []
        for (const member of members) {
          teamMembers.value.push({
            agent_id: member.agent_id,
            team_id: team.id,
            team_name: team.name
          })
        }
      } catch (e) {
        console.error('Failed to load team members for', team.name, e)
      }
    }
  } catch (e) {
    console.error('Failed to load agents:', e)
  }
}

// 加载模板
async function loadTemplate() {
  try {
    const res = await adminTeamApi.getTemplate()
    templateContent.value = res.data.content
  } catch (e) {
    console.error('Failed to load template:', e)
    templateContent.value = ''
  }
}

// 保存模板
async function saveTemplate() {
  try {
    await adminTeamApi.updateTemplate(templateContent.value)
    showTemplateModal.value = false
  } catch (e) {
    console.error('Failed to save template:', e)
  }
}

// 加载本团队知识列表
async function loadTeamKnowledge() {
  try {
    const res = await knowledgeApi.listMyTeamKnowledge()
    knowledgeList.value = res.data.items || []
    knowledgeTotal.value = res.data.total || 0
  } catch (e) {
    console.error('Failed to load knowledge:', e)
  }
}

// 上传知识
async function uploadKnowledge() {
  if (!knowledgeForm.value.title || !knowledgeForm.value.content) return
  try {
    await knowledgeApi.uploadKnowledge(knowledgeForm.value)
    knowledgeForm.value = { title: '', content: '' }
    showKnowledgeSheet.value = false
    knowledgeMode.value = 'list'
    await loadTeamKnowledge()
  } catch (e) {
    console.error('Failed to upload knowledge:', e)
  }
}

// 搜索知识
async function searchKnowledge() {
  if (!knowledgeSearchQuery.value.trim()) return
  try {
    const res = await knowledgeApi.searchKnowledge({ q: knowledgeSearchQuery.value })
    knowledgeSearchResults.value = res.data.items || []
    knowledgeSearchTotal.value = res.data.total || 0
    knowledgeMode.value = 'search'
  } catch (e) {
    console.error('Failed to search knowledge:', e)
  }
}

// 打开知识详情
function viewKnowledge(item: any) {
  selectedKnowledge.value = item
  showKnowledgeSheet.value = true
}

onMounted(async () => {
  loadTeams()
  loadAvailableAgents()
  loadTemplate()
  await loadTeamKnowledge()
})
</script>

<style scoped>
.teams-view {
  padding: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.teams-table {
  background: white;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  overflow: hidden;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
