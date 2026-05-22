<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">DevOps 流水线</div>
          <div class="text-[12px] text-[#717182] mt-1">管理 CI/CD 流水线配置，支持 GitHub Actions 触发和回调</div>
        </div>
        <button @click="showCreate = true" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded hover:bg-blue-700">新建流水线</button>
      </div>

      <!-- Create form -->
      <div v-if="showCreate" class="mb-4 p-4 border border-black/10 rounded bg-gray-50">
        <div class="text-[13px] font-medium mb-2">新建流水线</div>
        <div class="grid grid-cols-2 gap-3">
          <input v-model="form.name" placeholder="流水线名称" class="text-[12px] border rounded px-2 py-1" />
          <select v-model="form.provider" class="text-[12px] border rounded px-2 py-1">
            <option value="github_actions">GitHub Actions</option>
            <option value="jenkins">Jenkins</option>
          </select>
          <template v-if="form.provider === 'github_actions'">
            <input v-model="form.repoFullName" placeholder="仓库全名 (owner/repo)" class="text-[12px] border rounded px-2 py-1" />
            <input v-model="form.workflowFile" placeholder="工作流文件名 (.github/workflows/ci.yml)" class="text-[12px] border rounded px-2 py-1" />
            <input v-model="form.githubToken" placeholder="GitHub Token (仅用于触发)" type="password" class="text-[12px] border rounded px-2 py-1" />
            <input v-model="form.defaultBranch" placeholder="默认分支 (main)" class="text-[12px] border rounded px-2 py-1" />
          </template>
          <template v-else>
            <input v-model="form.baseUrl" placeholder="Jenkins Base URL (https://jenkins.example.com)" class="text-[12px] border rounded px-2 py-1" />
            <input v-model="form.jobName" placeholder="Job 名称" class="text-[12px] border rounded px-2 py-1" />
            <input v-model="form.username" placeholder="Jenkins 用户名" class="text-[12px] border rounded px-2 py-1" />
            <input v-model="form.apiToken" placeholder="Jenkins API Token" type="password" class="text-[12px] border rounded px-2 py-1" />
            <input v-model="form.crumb" placeholder="Crumb (可选)" class="text-[12px] border rounded px-2 py-1" />
            <input v-model="form.triggerToken" placeholder="Trigger Token (可选)" type="password" class="text-[12px] border rounded px-2 py-1" />
          </template>
        </div>
        <div class="mt-2 text-[11px] text-[#717182]">
          凭证仅保存到流水线配置 config 中，提交前请确认必填项完整。
        </div>
        <div v-if="formError" class="mt-2 text-[11px] text-red-600">{{ formError }}</div>
        <div class="flex gap-2 mt-3">
          <button @click="create" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded">创建</button>
          <button @click="closeCreate" class="text-[12px] px-3 py-1 border rounded">取消</button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-8 text-[12px] text-[#717182]">加载中...</div>
      <div v-else-if="pipelines.length === 0" class="text-center py-8 text-[12px] text-[#717182]">暂无流水线</div>
      <div v-else class="space-y-3">
        <div v-for="p in pipelines" :key="p.id" class="border border-black/10 rounded p-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-[14px] font-medium">{{ p.name }}</div>
              <div class="text-[11px] text-[#717182] mt-1">{{ p.provider }} · {{ p.repoFullName || '-' }} · {{ p.workflowFile || '-' }}</div>
            </div>
            <div class="flex items-center gap-2">
              <span :class="p.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'" class="px-2 py-0.5 rounded text-[11px]">
                {{ p.enabled ? '已启用' : '已禁用' }}
              </span>
              <span :class="pipelineStatusClass(p.status)" class="px-2 py-0.5 rounded text-[11px]">{{ p.status }}</span>
              <button @click="trigger(p.id)" class="text-[11px] px-2 py-0.5 bg-green-500 text-white rounded hover:bg-green-600">触发</button>
              <button @click="remove(p.id)" class="text-[11px] px-2 py-0.5 bg-red-500 text-white rounded hover:bg-red-600">删除</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Runs -->
      <div class="mt-6">
        <div class="text-[14px] font-semibold mb-3">执行记录</div>
        <div v-if="runs.length === 0" class="text-[12px] text-[#717182]">暂无执行记录</div>
        <table v-else class="w-full text-[12px]">
          <thead>
            <tr class="border-b border-black/5">
              <th class="text-left py-2 px-2 text-[#717182] font-medium">运行ID</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">流水线</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">状态</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">分支</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">触发方式</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">错误</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in runs" :key="r.id" class="border-b border-black/5">
              <td class="py-2 px-2 font-mono text-[11px]">{{ r.id.slice(0, 8) }}...</td>
              <td class="py-2 px-2 font-mono text-[11px]">{{ r.pipelineId.slice(0, 8) }}...</td>
              <td class="py-2 px-2"><span :class="runStatusClass(r.status)" class="px-2 py-0.5 rounded text-[11px]">{{ r.status }}</span></td>
              <td class="py-2 px-2">{{ r.branch || '-' }}</td>
              <td class="py-2 px-2">{{ r.triggerType }}</td>
              <td class="py-2 px-2 text-red-500 max-w-[150px] truncate">{{ r.errorMessage || '-' }}</td>
              <td class="py-2 px-2">{{ formatDate(r.createdAt) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { listPipelines, createPipeline, deletePipeline, triggerPipeline, listRuns, type DevOpsPipeline, type DevOpsRun } from '@/lib/api/devops'

const route = useRoute()
const projectId = route.params.projectId as string

const pipelines = ref<DevOpsPipeline[]>([])
const runs = ref<DevOpsRun[]>([])
const loading = ref(false)
const showCreate = ref(false)
const formError = ref('')
type Provider = 'github_actions' | 'jenkins'
type PipelineForm = {
  name: string
  provider: Provider
  repoFullName: string
  workflowFile: string
  githubToken: string
  defaultBranch: string
  baseUrl: string
  jobName: string
  username: string
  apiToken: string
  crumb: string
  triggerToken: string
}

const getInitialForm = (): PipelineForm => ({
  name: '',
  provider: 'github_actions',
  repoFullName: '',
  workflowFile: '',
  githubToken: '',
  defaultBranch: '',
  baseUrl: '',
  jobName: '',
  username: '',
  apiToken: '',
  crumb: '',
  triggerToken: '',
})

const form = ref<PipelineForm>(getInitialForm())

const pipelineStatusClass = (s: string) => ({ IDLE: 'bg-gray-100 text-gray-600', RUNNING: 'bg-blue-100 text-blue-700', SUCCESS: 'bg-green-100 text-green-700', FAILED: 'bg-red-100 text-red-700' })[s] || 'bg-gray-100'
const runStatusClass = (s: string) => ({ PENDING: 'bg-yellow-100 text-yellow-700', RUNNING: 'bg-blue-100 text-blue-700', SUCCESS: 'bg-green-100 text-green-700', FAILED: 'bg-red-100 text-red-700', CANCELED: 'bg-gray-100 text-gray-500' })[s] || 'bg-gray-100'
const formatDate = (ts: number) => new Date(ts * 1000).toLocaleString('zh-CN')

async function load() {
  loading.value = true
  try {
    const [pRes, rRes] = await Promise.all([
      listPipelines(projectId),
      listRuns(projectId),
    ])
    pipelines.value = pRes.items
    runs.value = rRes.items
  } finally {
    loading.value = false
  }
}

async function create() {
  formError.value = ''
  const name = form.value.name.trim()
  if (!name) {
    formError.value = '请填写流水线名称'
    return
  }

  const provider = form.value.provider
  const payload: {
    name: string
    provider: Provider
    repoFullName?: string
    workflowFile?: string
    config: Record<string, unknown>
  } = { name, provider, config: {} }

  if (provider === 'github_actions') {
    const repoFullName = form.value.repoFullName.trim()
    const workflowFile = form.value.workflowFile.trim()
    const githubToken = form.value.githubToken.trim()
    const defaultBranch = form.value.defaultBranch.trim()
    if (!repoFullName || !workflowFile || !githubToken || !defaultBranch) {
      formError.value = 'GitHub Actions 请填写 name、repo、workflow、token、defaultBranch'
      return
    }
    payload.repoFullName = repoFullName
    payload.workflowFile = workflowFile
    payload.config = { githubToken, defaultBranch }
  } else {
    const baseUrl = form.value.baseUrl.trim()
    const jobName = form.value.jobName.trim()
    const username = form.value.username.trim()
    const apiToken = form.value.apiToken.trim()
    if (!baseUrl || !jobName || !username || !apiToken) {
      formError.value = 'Jenkins 请填写 name、baseUrl、jobName、username、apiToken'
      return
    }
    const crumb = form.value.crumb.trim()
    const triggerToken = form.value.triggerToken.trim()
    payload.config = {
      baseUrl,
      jobName,
      username,
      apiToken,
      ...(crumb ? { crumb } : {}),
      ...(triggerToken ? { triggerToken } : {}),
    }
  }

  await createPipeline(projectId, payload)
  showCreate.value = false
  form.value = getInitialForm()
  formError.value = ''
  await load()
}

function closeCreate() {
  showCreate.value = false
  formError.value = ''
  form.value = getInitialForm()
}

async function remove(id: string) {
  await deletePipeline(projectId, id)
  await load()
}

async function trigger(id: string) {
  await triggerPipeline(projectId, id)
  await load()
}

onMounted(load)
</script>
