<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  listTrainingJobs,
  createTrainingJob,
  deleteTrainingJob,
  getTrainingJob,
  prepareDataset,
  startTraining,
  getTrainingProgress,
  listDatasets,
  createDataset,
  type AiTrainingJobListItem,
  type AiTrainingJobDetail,
  type AiTrainingJobProgress,
  type AiTrainingDatasetListItem,
  type AiTrainingJobCreatePayload,
  type AiTrainingDatasetCreatePayload
} from '@/lib/api/aiTraining'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || '').trim())

// State
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const saveError = ref('')
const successMessage = ref('')

// Tabs
const activeTab = ref<'jobs' | 'datasets'>('jobs')

// Training Jobs
const jobs = ref<AiTrainingJobListItem[]>([])
const jobsTotal = ref(0)
const jobsPage = ref(1)
const statusFilter = ref('')

// Datasets
const datasets = ref<AiTrainingDatasetListItem[]>([])
const datasetsTotal = ref(0)
const datasetsPage = ref(1)

// Modals
const showCreateJobModal = ref(false)
const showCreateDatasetModal = ref(false)
const showDetailModal = ref(false)
const selectedJob = ref<AiTrainingJobDetail | null>(null)
const trainingProgress = ref<AiTrainingJobProgress | null>(null)

// Forms
const jobForm = ref<AiTrainingJobCreatePayload>({
  name: '',
  description: '',
  trainingType: 'FINE_TUNE',
  baseModel: 'deepseek-chat',
  datasetConfig: {},
  hyperparams: { epochs: 3, learningRate: 0.001, batchSize: 16 }
})

const datasetForm = ref<AiTrainingDatasetCreatePayload>({
  name: '',
  sourceType: 'TESTCASES',
  config: {}
})

// Options
const trainingTypeOptions = [
  { value: 'FINE_TUNE', label: 'Fine-Tune' },
  { value: 'EMBEDDING', label: 'Embedding' },
  { value: 'CLASSIFIER', label: 'Classifier' }
]

const baseModelOptions = [
  { value: 'deepseek-chat', label: 'DeepSeek Chat' },
  { value: 'deepseek-coder', label: 'DeepSeek Coder' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'qwen-turbo', label: 'Qwen Turbo' }
]

const sourceTypeOptions = [
  { value: 'TESTCASES', label: '测试用例' },
  { value: 'REQUIREMENTS', label: '需求文档' },
  { value: 'DEFECTS', label: '缺陷数据' },
  { value: 'CUSTOM', label: '自定义' }
]

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'DRAFT', label: '草稿' },
  { value: 'PREPARING', label: '准备中' },
  { value: 'TRAINING', label: '训练中' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'FAILED', label: '失败' }
]

// ---------- Helpers ----------

function statusText(status: string): string {
  const map: Record<string, string> = {
    DRAFT: '草稿', PREPARING: '准备中', TRAINING: '训练中',
    COMPLETED: '已完成', FAILED: '失败'
  }
  return map[status] || status
}

function statusClass(status: string): string {
  const map: Record<string, string> = {
    DRAFT: 'text-gray-600 bg-gray-100',
    PREPARING: 'text-blue-600 bg-blue-100',
    TRAINING: 'text-amber-600 bg-amber-100',
    COMPLETED: 'text-green-600 bg-green-100',
    FAILED: 'text-red-600 bg-red-100'
  }
  return map[status] || 'text-gray-600 bg-gray-100'
}

function sourceTypeText(sourceType: string): string {
  const map: Record<string, string> = {
    TESTCASES: '测试用例', REQUIREMENTS: '需求文档',
    DEFECTS: '缺陷数据', CUSTOM: '自定义'
  }
  return map[sourceType] || sourceType
}

function formatTime(ts: number | null): string {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

function formatProgress(value: number): string {
  return `${Math.round(value * 100)}%`
}

// ---------- Data Loading ----------

async function loadJobs() {
  if (!projectId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await listTrainingJobs(projectId.value, {
      page: jobsPage.value,
      pageSize: 20,
      status: statusFilter.value || undefined
    })
    jobs.value = result.items
    jobsTotal.value = result.total
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadDatasets() {
  if (!projectId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await listDatasets(projectId.value, {
      page: datasetsPage.value,
      pageSize: 20
    })
    datasets.value = result.items
    datasetsTotal.value = result.total
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function loadData() {
  if (activeTab.value === 'jobs') {
    loadJobs()
  } else {
    loadDatasets()
  }
}

// ---------- Job Actions ----------

function resetJobForm() {
  jobForm.value = {
    name: '',
    description: '',
    trainingType: 'FINE_TUNE',
    baseModel: 'deepseek-chat',
    datasetConfig: {},
    hyperparams: { epochs: 3, learningRate: 0.001, batchSize: 16 }
  }
}

function openCreateJobModal() {
  resetJobForm()
  saveError.value = ''
  showCreateJobModal.value = true
}

function closeCreateJobModal() {
  showCreateJobModal.value = false
  saveError.value = ''
}

async function handleCreateJob() {
  if (!jobForm.value.name.trim()) {
    saveError.value = '请输入训练任务名称'
    return
  }
  saving.value = true
  saveError.value = ''
  try {
    await createTrainingJob(projectId.value, jobForm.value)
    successMessage.value = '训练任务创建成功'
    showCreateJobModal.value = false
    await loadJobs()
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    saving.value = false
  }
}

async function handleDeleteJob(id: string, name: string) {
  if (!confirm(`确定删除训练任务「${name}」吗？`)) return
  try {
    await deleteTrainingJob(projectId.value, id)
    successMessage.value = '删除成功'
    await loadJobs()
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '删除失败'
  }
}

async function openJobDetail(job: AiTrainingJobListItem) {
  try {
    const detail = await getTrainingJob(projectId.value, job.id)
    selectedJob.value = detail
    if (detail.status === 'TRAINING') {
      trainingProgress.value = await getTrainingProgress(projectId.value, job.id)
    } else {
      trainingProgress.value = null
    }
    showDetailModal.value = true
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '加载详情失败'
  }
}

function closeDetailModal() {
  showDetailModal.value = false
  selectedJob.value = null
  trainingProgress.value = null
}

async function handlePrepareDataset(jobId: string) {
  saving.value = true
  try {
    selectedJob.value = await prepareDataset(projectId.value, jobId)
    successMessage.value = '数据集准备完成'
    await loadJobs()
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '准备数据集失败'
  } finally {
    saving.value = false
  }
}

async function handleStartTraining(jobId: string) {
  saving.value = true
  try {
    selectedJob.value = await startTraining(projectId.value, jobId)
    trainingProgress.value = {
      status: selectedJob.value.status,
      progress: selectedJob.value.progress,
      metrics: selectedJob.value.metrics,
      modelRef: selectedJob.value.modelRef,
      errorMessage: selectedJob.value.errorMessage
    }
    successMessage.value = '训练完成'
    await loadJobs()
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '训练启动失败'
  } finally {
    saving.value = false
  }
}

async function handleRefreshProgress(jobId: string) {
  try {
    trainingProgress.value = await getTrainingProgress(projectId.value, jobId)
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '获取进度失败'
  }
}

// ---------- Dataset Actions ----------

function resetDatasetForm() {
  datasetForm.value = { name: '', sourceType: 'TESTCASES', config: {} }
}

function openCreateDatasetModal() {
  resetDatasetForm()
  saveError.value = ''
  showCreateDatasetModal.value = true
}

function closeCreateDatasetModal() {
  showCreateDatasetModal.value = false
  saveError.value = ''
}

async function handleCreateDataset() {
  if (!datasetForm.value.name.trim()) {
    saveError.value = '请输入数据集名称'
    return
  }
  saving.value = true
  saveError.value = ''
  try {
    await createDataset(projectId.value, datasetForm.value)
    successMessage.value = '数据集创建成功'
    showCreateDatasetModal.value = false
    await loadDatasets()
    setTimeout(() => { successMessage.value = '' }, 3000)
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    saving.value = false
  }
}

// ---------- Lifecycle ----------

onMounted(loadData)
</script>

<template>
  <div class="p-6 max-w-[1200px] mx-auto">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-[#0A0A0A]">AI 模型训练</h1>
        <p class="text-sm text-[rgba(10,10,10,0.5)] mt-1">基于项目数据训练自定义 AI 模型，支持 Fine-Tune、Embedding 和分类器</p>
      </div>
      <div class="flex gap-2">
        <button
          v-if="activeTab === 'jobs'"
          type="button"
          class="px-4 py-2 bg-[#155DFC] text-white rounded-lg text-sm font-medium hover:bg-[#0D47C4] transition-colors"
          @click="openCreateJobModal"
        >
          创建训练任务
        </button>
        <button
          v-if="activeTab === 'datasets'"
          type="button"
          class="px-4 py-2 bg-[#155DFC] text-white rounded-lg text-sm font-medium hover:bg-[#0D47C4] transition-colors"
          @click="openCreateDatasetModal"
        >
          创建数据集
        </button>
      </div>
    </div>

    <!-- Messages -->
    <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{{ errorMessage }}</div>
    <div v-if="successMessage" class="mb-4 p-3 bg-green-50 text-green-600 rounded-lg text-sm">{{ successMessage }}</div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-6 border-b border-[#E5E5E5]">
      <button
        type="button"
        class="px-4 py-2 text-sm font-medium transition-colors border-b-2"
        :class="activeTab === 'jobs' ? 'text-[#155DFC] border-[#155DFC]' : 'text-[rgba(10,10,10,0.5)] border-transparent hover:text-[#0A0A0A]'"
        @click="activeTab = 'jobs'; loadData()"
      >
        训练任务
      </button>
      <button
        type="button"
        class="px-4 py-2 text-sm font-medium transition-colors border-b-2"
        :class="activeTab === 'datasets' ? 'text-[#155DFC] border-[#155DFC]' : 'text-[rgba(10,10,10,0.5)] border-transparent hover:text-[#0A0A0A]'"
        @click="activeTab = 'datasets'; loadData()"
      >
        数据集
      </button>
    </div>

    <!-- Training Jobs Tab -->
    <div v-if="activeTab === 'jobs'">
      <!-- Filter -->
      <div class="flex gap-3 mb-4">
        <select
          v-model="statusFilter"
          class="px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
          @change="jobsPage = 1; loadJobs()"
        >
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>

      <div v-if="loading" class="text-center py-12 text-[rgba(10,10,10,0.5)]">加载中...</div>

      <div v-else-if="jobs.length === 0" class="text-center py-16 bg-[#FAFAFA] rounded-xl border border-[#E5E5E5]">
        <div class="text-[rgba(10,10,10,0.4)] text-lg mb-2">暂无训练任务</div>
        <div class="text-[rgba(10,10,10,0.3)] text-sm">点击「创建训练任务」开始训练自定义模型</div>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="job in jobs"
          :key="job.id"
          class="bg-white rounded-xl border border-[#E5E5E5] p-5 hover:shadow-sm transition-shadow cursor-pointer"
          @click="openJobDetail(job)"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-2">
                <span class="font-medium text-[#0A0A0A]">{{ job.name }}</span>
                <span :class="statusClass(job.status)" class="px-2 py-0.5 rounded text-xs font-medium">
                  {{ statusText(job.status) }}
                </span>
                <span class="px-2 py-0.5 bg-[#F0F4FF] text-[#155DFC] rounded text-xs">
                  {{ job.trainingType }}
                </span>
                <span class="text-xs text-[rgba(10,10,10,0.45)]">{{ job.baseModel }}</span>
              </div>
              <div v-if="job.description" class="text-sm text-[rgba(10,10,10,0.6)] mb-2">{{ job.description }}</div>
              <div class="flex items-center gap-4 text-xs text-[rgba(10,10,10,0.45)]">
                <span>进度：{{ formatProgress(job.progress) }}</span>
                <span v-if="job.metrics.loss !== undefined">Loss: {{ job.metrics.loss }}</span>
                <span v-if="job.metrics.accuracy !== undefined">准确率: {{ job.metrics.accuracy }}</span>
                <span>创建时间：{{ formatTime(job.createdAt) }}</span>
              </div>
              <!-- Progress bar -->
              <div v-if="job.status === 'TRAINING'" class="mt-3 w-full bg-gray-200 rounded-full h-2">
                <div
                  class="bg-amber-500 h-2 rounded-full transition-all duration-300"
                  :style="{ width: formatProgress(job.progress) }"
                ></div>
              </div>
              <div v-if="job.status === 'COMPLETED' && job.modelRef" class="mt-2 text-xs text-green-600 bg-green-50 px-2 py-1 rounded inline-block">
                模型：{{ job.modelRef }}
              </div>
              <div v-if="job.status === 'FAILED' && job.errorMessage" class="mt-2 text-xs text-red-500 bg-red-50 px-2 py-1 rounded">
                {{ job.errorMessage }}
              </div>
            </div>
            <button
              type="button"
              class="px-3 py-1.5 text-sm text-red-500 hover:bg-red-50 rounded-lg transition-colors ml-4"
              @click.stop="handleDeleteJob(job.id, job.name)"
            >
              删除
            </button>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="jobsTotal > 20" class="flex justify-center gap-2 mt-4">
          <button
            type="button"
            class="px-3 py-1.5 text-sm border border-[#E5E5E5] rounded-lg disabled:opacity-50"
            :disabled="jobsPage <= 1"
            @click="jobsPage--; loadJobs()"
          >
            上一页
          </button>
          <span class="px-3 py-1.5 text-sm text-[rgba(10,10,10,0.5)]">
            {{ jobsPage }} / {{ Math.ceil(jobsTotal / 20) }}
          </span>
          <button
            type="button"
            class="px-3 py-1.5 text-sm border border-[#E5E5E5] rounded-lg disabled:opacity-50"
            :disabled="jobsPage >= Math.ceil(jobsTotal / 20)"
            @click="jobsPage++; loadJobs()"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

    <!-- Datasets Tab -->
    <div v-if="activeTab === 'datasets'">
      <div v-if="loading" class="text-center py-12 text-[rgba(10,10,10,0.5)]">加载中...</div>

      <div v-else-if="datasets.length === 0" class="text-center py-16 bg-[#FAFAFA] rounded-xl border border-[#E5E5E5]">
        <div class="text-[rgba(10,10,10,0.4)] text-lg mb-2">暂无数据集</div>
        <div class="text-[rgba(10,10,10,0.3)] text-sm">点击「创建数据集」从项目数据中创建训练数据集</div>
      </div>

      <div v-else class="grid gap-4 md:grid-cols-2">
        <div
          v-for="ds in datasets"
          :key="ds.id"
          class="bg-white rounded-xl border border-[#E5E5E5] p-5 hover:shadow-sm transition-shadow"
        >
          <div class="flex items-center gap-3 mb-2">
            <span class="font-medium text-[#0A0A0A]">{{ ds.name }}</span>
            <span class="px-2 py-0.5 bg-[#F0F4FF] text-[#155DFC] rounded text-xs">
              {{ sourceTypeText(ds.sourceType) }}
            </span>
          </div>
          <div class="text-sm text-[rgba(10,10,10,0.6)] mb-2">记录数：{{ ds.recordCount }}</div>
          <div class="text-xs text-[rgba(10,10,10,0.45)]">创建时间：{{ formatTime(ds.createdAt) }}</div>
          <!-- Sample preview -->
          <div v-if="ds.sampleJson?.samples && Array.isArray(ds.sampleJson.samples) && ds.sampleJson.samples.length > 0" class="mt-3 border-t border-[#E5E5E5] pt-3">
            <div class="text-xs text-[rgba(10,10,10,0.45)] mb-1">样本预览：</div>
            <div class="max-h-24 overflow-y-auto text-xs text-[rgba(10,10,10,0.6)] bg-[#FAFAFA] rounded p-2">
              <div v-for="(sample, idx) in (ds.sampleJson.samples as Record<string, unknown>[]).slice(0, 3)" :key="idx" class="mb-1 last:mb-0">
                {{ JSON.stringify(sample).substring(0, 120) }}{{ JSON.stringify(sample).length > 120 ? '...' : '' }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="datasetsTotal > 20" class="flex justify-center gap-2 mt-4">
        <button
          type="button"
          class="px-3 py-1.5 text-sm border border-[#E5E5E5] rounded-lg disabled:opacity-50"
          :disabled="datasetsPage <= 1"
          @click="datasetsPage--; loadDatasets()"
        >
          上一页
        </button>
        <span class="px-3 py-1.5 text-sm text-[rgba(10,10,10,0.5)]">
          {{ datasetsPage }} / {{ Math.ceil(datasetsTotal / 20) }}
        </span>
        <button
          type="button"
          class="px-3 py-1.5 text-sm border border-[#E5E5E5] rounded-lg disabled:opacity-50"
          :disabled="datasetsPage >= Math.ceil(datasetsTotal / 20)"
          @click="datasetsPage++; loadDatasets()"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- Create Job Modal -->
    <Teleport to="body">
      <div v-if="showCreateJobModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/30" @click="closeCreateJobModal"></div>
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
          <h2 class="text-lg font-semibold text-[#0A0A0A] mb-4">创建训练任务</h2>

          <div v-if="saveError" class="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{{ saveError }}</div>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">任务名称</label>
              <input
                v-model="jobForm.name"
                type="text"
                placeholder="例如：测试用例生成模型"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">描述</label>
              <textarea
                v-model="jobForm.description"
                rows="2"
                placeholder="任务描述（可选）"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              ></textarea>
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">训练类型</label>
              <select
                v-model="jobForm.trainingType"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              >
                <option v-for="opt in trainingTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">基础模型</label>
              <select
                v-model="jobForm.baseModel"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              >
                <option v-for="opt in baseModelOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>

            <div class="grid grid-cols-3 gap-3">
              <div>
                <label class="block text-sm font-medium text-[#0A0A0A] mb-1">Epochs</label>
                <input
                  v-model.number="(jobForm.hyperparams as Record<string, number>).epochs"
                  type="number"
                  min="1"
                  max="100"
                  class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-[#0A0A0A] mb-1">Learning Rate</label>
                <input
                  v-model.number="(jobForm.hyperparams as Record<string, number>).learningRate"
                  type="number"
                  step="0.0001"
                  min="0.0001"
                  max="1"
                  class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-[#0A0A0A] mb-1">Batch Size</label>
                <input
                  v-model.number="(jobForm.hyperparams as Record<string, number>).batchSize"
                  type="number"
                  min="1"
                  max="256"
                  class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
                />
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button
              type="button"
              class="px-4 py-2 text-sm text-[rgba(10,10,10,0.7)] hover:bg-[#F5F5F5] rounded-lg transition-colors"
              @click="closeCreateJobModal"
            >
              取消
            </button>
            <button
              type="button"
              class="px-4 py-2 bg-[#155DFC] text-white rounded-lg text-sm font-medium hover:bg-[#0D47C4] transition-colors disabled:opacity-50"
              :disabled="saving"
              @click="handleCreateJob"
            >
              {{ saving ? '创建中...' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Create Dataset Modal -->
    <Teleport to="body">
      <div v-if="showCreateDatasetModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/30" @click="closeCreateDatasetModal"></div>
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
          <h2 class="text-lg font-semibold text-[#0A0A0A] mb-4">创建数据集</h2>

          <div v-if="saveError" class="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{{ saveError }}</div>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">数据集名称</label>
              <input
                v-model="datasetForm.name"
                type="text"
                placeholder="例如：回归测试数据集"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-[#0A0A0A] mb-1">数据来源</label>
              <select
                v-model="datasetForm.sourceType"
                class="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC]"
              >
                <option v-for="opt in sourceTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button
              type="button"
              class="px-4 py-2 text-sm text-[rgba(10,10,10,0.7)] hover:bg-[#F5F5F5] rounded-lg transition-colors"
              @click="closeCreateDatasetModal"
            >
              取消
            </button>
            <button
              type="button"
              class="px-4 py-2 bg-[#155DFC] text-white rounded-lg text-sm font-medium hover:bg-[#0D47C4] transition-colors disabled:opacity-50"
              :disabled="saving"
              @click="handleCreateDataset"
            >
              {{ saving ? '创建中...' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Job Detail Modal -->
    <Teleport to="body">
      <div v-if="showDetailModal && selectedJob" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/30" @click="closeDetailModal"></div>
        <div class="relative bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 p-6 max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-[#0A0A0A]">{{ selectedJob.name }}</h2>
            <button
              type="button"
              class="text-[rgba(10,10,10,0.4)] hover:text-[#0A0A0A] text-xl"
              @click="closeDetailModal"
            >
              &times;
            </button>
          </div>

          <!-- Status & Progress -->
          <div class="mb-6">
            <div class="flex items-center gap-3 mb-3">
              <span :class="statusClass(selectedJob.status)" class="px-2 py-0.5 rounded text-xs font-medium">
                {{ statusText(selectedJob.status) }}
              </span>
              <span class="px-2 py-0.5 bg-[#F0F4FF] text-[#155DFC] rounded text-xs">{{ selectedJob.trainingType }}</span>
              <span class="text-xs text-[rgba(10,10,10,0.45)]">{{ selectedJob.baseModel }}</span>
            </div>

            <!-- Progress bar -->
            <div v-if="selectedJob.status === 'TRAINING' || selectedJob.status === 'COMPLETED'" class="mb-3">
              <div class="flex justify-between text-xs text-[rgba(10,10,10,0.5)] mb-1">
                <span>训练进度</span>
                <span>{{ formatProgress(selectedJob.progress) }}</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-3">
                <div
                  class="h-3 rounded-full transition-all duration-300"
                  :class="selectedJob.status === 'COMPLETED' ? 'bg-green-500' : 'bg-amber-500'"
                  :style="{ width: formatProgress(selectedJob.progress) }"
                ></div>
              </div>
            </div>

            <div v-if="selectedJob.description" class="text-sm text-[rgba(10,10,10,0.6)]">{{ selectedJob.description }}</div>
          </div>

          <!-- Metrics -->
          <div v-if="selectedJob.status === 'COMPLETED' && selectedJob.metrics" class="mb-6">
            <h3 class="text-sm font-medium text-[#0A0A0A] mb-3">训练指标</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div class="bg-[#FAFAFA] rounded-lg p-3 text-center">
                <div class="text-lg font-semibold text-[#0A0A0A]">{{ selectedJob.metrics.loss ?? '-' }}</div>
                <div class="text-xs text-[rgba(10,10,10,0.45)]">Loss</div>
              </div>
              <div class="bg-[#FAFAFA] rounded-lg p-3 text-center">
                <div class="text-lg font-semibold text-[#0A0A0A]">{{ selectedJob.metrics.accuracy ?? '-' }}</div>
                <div class="text-xs text-[rgba(10,10,10,0.45)]">准确率</div>
              </div>
              <div class="bg-[#FAFAFA] rounded-lg p-3 text-center">
                <div class="text-lg font-semibold text-[#0A0A0A]">{{ selectedJob.metrics.evalScore ?? '-' }}</div>
                <div class="text-xs text-[rgba(10,10,10,0.45)]">Eval Score</div>
              </div>
              <div class="bg-[#FAFAFA] rounded-lg p-3 text-center">
                <div class="text-lg font-semibold text-[#0A0A0A]">{{ selectedJob.metrics.epochs ?? '-' }}</div>
                <div class="text-xs text-[rgba(10,10,10,0.45)]">Epochs</div>
              </div>
            </div>
          </div>

          <!-- Model Reference -->
          <div v-if="selectedJob.modelRef" class="mb-6">
            <h3 class="text-sm font-medium text-[#0A0A0A] mb-2">模型部署引用</h3>
            <div class="bg-green-50 text-green-700 rounded-lg p-3 text-sm font-mono break-all">
              {{ selectedJob.modelRef }}
            </div>
          </div>

          <!-- Dataset Config -->
          <div v-if="selectedJob.datasetConfig" class="mb-6">
            <h3 class="text-sm font-medium text-[#0A0A0A] mb-2">数据集配置</h3>
            <div class="bg-[#FAFAFA] rounded-lg p-3 text-xs text-[rgba(10,10,10,0.6)] overflow-x-auto">
              <pre class="whitespace-pre-wrap">{{ JSON.stringify(selectedJob.datasetConfig, null, 2) }}</pre>
            </div>
          </div>

          <!-- Hyperparams -->
          <div v-if="selectedJob.hyperparams" class="mb-6">
            <h3 class="text-sm font-medium text-[#0A0A0A] mb-2">超参数</h3>
            <div class="bg-[#FAFAFA] rounded-lg p-3 text-xs text-[rgba(10,10,10,0.6)] overflow-x-auto">
              <pre class="whitespace-pre-wrap">{{ JSON.stringify(selectedJob.hyperparams, null, 2) }}</pre>
            </div>
          </div>

          <!-- Error -->
          <div v-if="selectedJob.status === 'FAILED' && selectedJob.errorMessage" class="mb-6">
            <h3 class="text-sm font-medium text-red-600 mb-2">错误信息</h3>
            <div class="bg-red-50 text-red-600 rounded-lg p-3 text-sm">{{ selectedJob.errorMessage }}</div>
          </div>

          <!-- Actions -->
          <div class="flex justify-end gap-3 mt-6 border-t border-[#E5E5E5] pt-4">
            <button
              v-if="selectedJob.status === 'DRAFT' || selectedJob.status === 'FAILED'"
              type="button"
              class="px-4 py-2 text-sm border border-[#155DFC] text-[#155DFC] rounded-lg hover:bg-[#F0F4FF] transition-colors disabled:opacity-50"
              :disabled="saving"
              @click="handlePrepareDataset(selectedJob!.id)"
            >
              {{ saving ? '准备中...' : '准备数据集' }}
            </button>
            <button
              v-if="selectedJob.status === 'DRAFT'"
              type="button"
              class="px-4 py-2 bg-[#155DFC] text-white rounded-lg text-sm font-medium hover:bg-[#0D47C4] transition-colors disabled:opacity-50"
              :disabled="saving"
              @click="handleStartTraining(selectedJob!.id)"
            >
              {{ saving ? '训练中...' : '开始训练' }}
            </button>
            <button
              v-if="selectedJob.status === 'TRAINING'"
              type="button"
              class="px-4 py-2 text-sm border border-[#E5E5E5] rounded-lg hover:bg-[#F5F5F5] transition-colors"
              @click="handleRefreshProgress(selectedJob!.id)"
            >
              刷新进度
            </button>
            <button
              type="button"
              class="px-4 py-2 text-sm text-[rgba(10,10,10,0.7)] hover:bg-[#F5F5F5] rounded-lg transition-colors"
              @click="closeDetailModal"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
