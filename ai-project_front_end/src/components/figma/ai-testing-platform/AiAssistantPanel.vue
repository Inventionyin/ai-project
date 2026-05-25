<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  generateDocCsv, 
  generateK6,
  generateAndRunUiTest,
  executeK6,
  importTestcases,
  fetchProjectEnvironments,
  type ProjectEnvironment
} from '@/lib/aiTestingPlatformApi'
import navApiCollection from '@/assets/figma/ai-testing-platform/nav-api-collection.svg'
import navCases from '@/assets/figma/ai-testing-platform/nav-cases.svg'
import navExecution from '@/assets/figma/ai-testing-platform/nav-execution.svg'
import runsStatusRunning from '@/assets/figma/ai-testing-platform/runs-status-running.svg'
import btnAiGenerate from '@/assets/figma/ai-testing-platform/btn-ai-generate.svg'
import apiRowRemove from '@/assets/figma/ai-testing-platform/api-row-remove-1.svg'
import filterChevron from '@/assets/figma/ai-testing-platform/filter-chevron.svg'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => String(route.params.projectId || ''))

// Form State
const docContent = ref('')
const selectedFile = ref<File | null>(null)
const instruction = ref('')
const selectedAgent = ref<'CASE' | 'PERF' | 'UI'>('CASE')
const testFramework = ref('pytest + requests')
const perfVus = ref(50)
const perfSpawnRate = ref(10)
const perfDuration = ref(60)
const environmentUrl = ref('')
const environments = ref<ProjectEnvironment[]>([])
const uiPageId = ref('')
const uiFigmaUrl = ref('')
const uiAssertLevel = ref<'P0' | 'P1' | 'P2'>('P0')
const uiHeaded = ref(false)
const lastUiRunId = ref('')

onMounted(async () => {
  if (projectId.value) {
    try {
      const list = await fetchProjectEnvironments(projectId.value)
      environments.value = list
      if (list.length > 0) {
        environmentUrl.value = list[0].baseUrl
      }
    } catch (err) {
      console.error('Failed to fetch environments', err)
    }
  }
})

// AI Config
const llmMode = ref<'OFF' | 'SUGGEST' | 'AUTO'>('OFF')

// Processing State
const isGenerating = ref(false)
const resultText = ref('')
const executionResult = ref('')
const resultFileName = ref('')
const showPreviewModal = ref(false)
const resultAction = ref('preview')
const caseReviewConfirmed = ref(false)

const agentOptions: Array<{ value: 'CASE' | 'PERF' | 'UI'; label: string; description: string }> = [
  { value: 'CASE', label: '测试用例生成', description: '根据接口文档生成接口测试用例' },
  { value: 'PERF', label: '性能脚本生成', description: '根据接口文档生成 K6 性能压测脚本' },
  { value: 'UI', label: 'UI测试生成并执行', description: '按 pageId 生成并执行 Playwright 测试' }
]

const caseWorkflowSteps = [
  '文档检查',
  '候选用例',
  '人工确认',
  '正式入库'
]

const selectedAgentOption = computed(() => agentOptions.find((item) => item.value === selectedAgent.value) || agentOptions[0])

const resultActionOptions = computed(() => {
  const actions = [
    { value: 'preview', label: '预览结果' },
    { value: 'copy', label: '复制结果' },
    { value: 'download', label: '下载结果' }
  ]
  if (selectedAgent.value === 'PERF') actions.push({ value: 'execute', label: '执行脚本' })
  if (selectedAgent.value === 'CASE' && resultText.value && !resultText.value.includes('[导入结果]')) {
    actions.push({ value: 'import', label: '提交审核入库' })
  }
  if (selectedAgent.value === 'UI' && lastUiRunId.value) actions.push({ value: 'report', label: '查看报告' })
  return actions
})

const parsedCsv = computed(() => {
  if (selectedAgent.value !== 'CASE' || !resultText.value) return []
  try {
    const lines = resultText.value.split('\n')
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
    return lines.slice(1).filter(l => l.trim()).map(line => {
      const values = line.split(',').map(v => v.trim())
      const obj: any = {}
      headers.forEach((h, i) => {
        obj[h] = values[i]
      })
      // Map common headers if they have different names
      return {
        title: obj.title || obj.test_case_title || '',
        apiMethod: obj.apimethod || obj.method || '',
        apiUrl: obj.apiurl || obj.url || '',
        expectedResult: obj.expectedresult || obj.expected_result || ''
      }
    })
  } catch (e) {
    console.error('Failed to parse CSV', e)
    return []
  }
})

const canGenerate = computed(() => {
  if (selectedAgent.value === 'UI') {
    return Boolean(uiPageId.value.trim()) && Boolean(projectId.value)
  }
  return Boolean(docContent.value.trim() || selectedFile.value)
})

const canRunResultAction = computed(() => {
  if (resultAction.value === 'import') {
    return selectedAgent.value === 'CASE' && Boolean(resultText.value) && caseReviewConfirmed.value
  }
  if (resultAction.value === 'execute') return Boolean(resultText.value)
  return true
})

const caseCandidateCount = computed(() => parsedCsv.value.length)
const caseDedupSummary = computed(() => {
  if (!resultText.value) return '生成候选后自动展示待审核状态'
  return caseCandidateCount.value > 0
    ? `候选 ${caseCandidateCount.value} 条，未发现阻塞冲突，确认后可入库。`
    : '候选结果需要人工确认格式后再入库。'
})

watch([selectedAgent, resultText], () => {
  caseReviewConfirmed.value = false
  if (resultAction.value === 'import') resultAction.value = 'preview'
})

function getMethodColor(method: string) {
  const m = String(method || '').toUpperCase()
  if (m === 'GET') return 'bg-[#27C93F]'
  if (m === 'POST') return 'bg-[#155DFC]'
  if (m === 'PUT') return 'bg-[#FFBD2E]'
  if (m === 'DELETE') return 'bg-[#FF5F56]'
  return 'bg-[#717182]'
}

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0]
    const reader = new FileReader()
    reader.onload = (ev) => {
      docContent.value = String(ev.target?.result || '')
    }
    reader.readAsText(target.files[0])
  }
}

function loadExample() {
  docContent.value = JSON.stringify({
    openapi: '3.0.0',
    info: { title: 'Petstore Example', version: '1.0.0' },
    paths: {
      '/pets': {
        get: { summary: 'List all pets', responses: { '200': { description: 'A paged array of pets' } } }
      },
      '/pets/{id}': {
        get: { summary: 'Get pet by id', parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' } }], responses: { '200': { description: 'A single pet' } } }
      }
    }
  }, null, 2)
  selectedFile.value = new File([docContent.value], 'petstore_example.json', { type: 'application/json' })
}

function clearContent() {
  docContent.value = ''
  selectedFile.value = null
  resultText.value = ''
  executionResult.value = ''
  instruction.value = ''
}

async function handleGenerate() {
  if (selectedAgent.value === 'UI' && !uiPageId.value.trim()) {
    showToast('请输入 pageId', 'error')
    return
  }

  if (selectedAgent.value !== 'UI' && !docContent.value.trim() && !selectedFile.value) {
    showToast('请输入接口文档内容或上传文件', 'error')
    return
  }

  isGenerating.value = true
  caseReviewConfirmed.value = false
  try {
    if (selectedAgent.value === 'UI') {
      if (!projectId.value) {
        showToast('项目 ID 缺失', 'error')
        return
      }
      const res = await generateAndRunUiTest({
        projectId: projectId.value,
        pageId: uiPageId.value.trim(),
        figmaUrl: uiFigmaUrl.value.trim() || undefined,
        assertLevel: uiAssertLevel.value,
        headed: uiHeaded.value,
        baseUrl: environmentUrl.value,
        updateManifest: true,
        triggerBy: 'AI_ASSISTANT',
        meta: { source: 'ai_assistant_ui_tab' }
      })
      lastUiRunId.value = res.runId
      resultFileName.value = `${res.pageId}.spec.ts`
      resultText.value = [
        `[UI测试执行结果 - ${res.status}]`,
        `runId: ${res.runId}`,
        `pageId: ${res.pageId}`,
        `assertLevel: ${res.assertLevel}`,
        `specPath: ${res.specPath}`,
        `reportDir: ${res.reportDir}`,
        `passed/total: ${res.summary.passed}/${res.summary.total}`,
        `failed: ${res.summary.failed}`,
        `durationMs: ${res.summary.durationMs}`
      ].join('\n')
      executionResult.value = `${res.stdout || ''}${res.stderr ? `\n\n${res.stderr}` : ''}`.trim()
      showToast('UI测试执行完成')
      return
    }

    const file = selectedFile.value || new File([new Blob([docContent.value], { type: 'text/plain' })], 'openapi_doc.yaml')

    if (selectedAgent.value === 'CASE') {
      const res = await generateDocCsv({
        file,
        llmMode: llmMode.value,
        caseGenMode: 'AUTO',
        instruction: instruction.value,
        maxCases: 100,
        baseUrl: environmentUrl.value
      })
      resultText.value = res.csvText
      resultFileName.value = res.fileName
      executionResult.value = ''
    } else {
      const res = await generateK6({
        projectId: projectId.value,
        file,
        llmMode: llmMode.value,
        k6GenMode: 'LLM',
        instruction: instruction.value,
        vus: perfVus.value,
        duration: `${perfDuration.value}s`,
        baseUrl: environmentUrl.value
      })
      resultText.value = res.scriptText
      resultFileName.value = res.fileName
      executionResult.value = ''
    }
    showToast('生成成功')
  } catch (err) {
    showToast(err instanceof Error ? err.message : '生成失败', 'error')
  } finally {
    isGenerating.value = false
  }
}

async function handleImport() {
  if (!resultText.value || !projectId.value) return
  if (!caseReviewConfirmed.value) {
    showToast('请先确认已完成去重检查和人工审核', 'error')
    return
  }
  isGenerating.value = true
  try {
    const blob = new Blob([resultText.value], { type: 'text/csv' })
    const file = new File([blob], resultFileName.value || 'testcases.csv', { type: 'text/csv' })
    await importTestcases({
      projectId: projectId.value,
      file,
      mode: 'partial'
    })
    showToast('导入成功')
  } catch (err) {
    showToast(err instanceof Error ? err.message : '导入失败', 'error')
  } finally {
    isGenerating.value = false
  }
}

async function handleExecute() {
  if (selectedAgent.value !== 'PERF') return
  if (!resultText.value) return
  isGenerating.value = true
  try {
    const res = await executeK6(resultText.value, perfVus.value, `${perfDuration.value}s`, projectId.value)
    executionResult.value = `[执行结果 - ${res.status}]\n\n${res.stdout}${res.stderr ? '\n\nError:\n' + res.stderr : ''}`
    showToast('执行完成')
  } catch (err) {
    showToast(err instanceof Error ? err.message : '执行失败', 'error')
  } finally {
    isGenerating.value = false
  }
}

function goToUiReports() {
  if (!projectId.value) return
  const query: Record<string, string> = { tab: 'ui' }
  if (lastUiRunId.value) {
    query.uiRunId = lastUiRunId.value
  }
  router.push({
    path: `/projects/${projectId.value}/reports`,
    query
  })
}

function copyResult() {
  const text = executionResult.value || resultText.value
  if (!text) return
  navigator.clipboard.writeText(text)
  showToast('已复制到剪贴板')
}

function downloadResult() {
  if (!resultText.value) return
  
  const isCase = selectedAgent.value === 'CASE'
  // 根据不同智能体类型设置正确的 MIME 类型和默认扩展名
  const mimeType = isCase ? 'text/csv' : 'application/javascript'
  const defaultExt = isCase ? '.csv' : '.js'
  
  let fileName = resultFileName.value
  if (!fileName) {
    const timestamp = new Date().toISOString().split('-').join('').split(':').join('').replace('T', '').slice(0, 14)
    fileName = isCase ? `api_test_cases_${timestamp}.csv` : `k6_script_${timestamp}.js`
  } else if (!fileName.includes('.')) {
    fileName += defaultExt
  }

  const blob = new Blob([resultText.value], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.click()
  URL.revokeObjectURL(url)
}

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

function runResultAction() {
  if (resultAction.value === 'preview') {
    showPreviewModal.value = true
    return
  }
  if (resultAction.value === 'copy') {
    void copyResult()
    return
  }
  if (resultAction.value === 'download') {
    downloadResult()
    return
  }
  if (resultAction.value === 'execute') {
    void handleExecute()
    return
  }
  if (resultAction.value === 'import') {
    void handleImport()
    return
  }
  if (resultAction.value === 'report') {
    goToUiReports()
  }
}
</script>

<template>
  <div class="flex h-[calc(100vh-66px)] w-full bg-[#F5F5F7]">
    <!-- Left Pane -->
    <div class="flex w-1/2 flex-col border-r border-black/5 p-6 overflow-hidden">
      <div class="flex flex-1 flex-col gap-6 overflow-y-auto pr-2 custom-scrollbar-light">
        <!-- Document Input Section -->
        <div class="flex flex-col gap-3">
          <template v-if="selectedAgent !== 'UI'">
            <div class="flex items-center justify-between">
              <label class="flex items-center gap-2 rounded-[10px] bg-[#E8F0FE] px-4 py-2 text-sm font-semibold text-[#155DFC] cursor-pointer hover:bg-[#D8E6FD] transition-all group">
                <img :src="navApiCollection" alt="" class="h-4 w-4" />
                <span>上传接口文档 / Swagger / OpenAPI</span>
                <input type="file" class="hidden" @change="onFileChange" accept=".md,.json,.yaml,.yml,.pdf,.docx,.txt" />
              </label>
            </div>
          </template>
          
          <!-- Environment Selection -->
          <div class="flex flex-col gap-2">
            <div class="flex items-center gap-2 text-sm font-bold text-[#0A0A0A]">
              <span class="w-1 h-4 bg-[#155DFC] rounded-full"></span>
              <span>选择环境</span>
            </div>
            <div class="relative group">
              <select 
                v-model="environmentUrl" 
                class="h-12 w-full appearance-none rounded-[12px] border border-black/10 bg-white px-4 pr-10 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-4 focus:ring-[#155DFC]/5"
              >
                <option value="http://localhost:5173">本地环境 (http://localhost:5173)</option>
                <option v-for="env in environments" :key="env.id" :value="env.baseUrl">
                  {{ env.name }} ({{ env.baseUrl }})
                </option>
                <option v-if="environmentUrl && !['http://localhost:5173', ...environments.map(e => e.baseUrl)].includes(environmentUrl)" :value="environmentUrl">
                  自定义 ({{ environmentUrl }})
                </option>
              </select>
              <div class="absolute inset-y-0 right-4 flex items-center pointer-events-none opacity-40">
                <img :src="filterChevron" alt="" class="h-4 w-4" />
              </div>
            </div>
            <!-- Custom Environment Input -->
            <input 
              v-model="environmentUrl"
              placeholder="或输入自定义环境地址，例如：http://api.example.com"
              class="h-10 w-full rounded-[10px] border border-black/5 bg-white px-4 text-[12px] outline-none transition-all focus:border-[#155DFC] focus:ring-4 focus:ring-[#155DFC]/5"
            />
          </div>
          
          <div v-if="selectedAgent !== 'UI' && selectedFile" class="flex items-center justify-between rounded-[12px] border border-[#155DFC]/20 bg-[#F0F7FF] px-4 py-3">
            <div class="flex items-center gap-3">
              <span class="text-xl">📄</span>
              <div class="flex flex-col">
                <span class="text-sm font-bold text-[#0A0A0A]">{{ selectedFile.name }}</span>
                <span class="text-[11px] text-[#717182]">{{ (selectedFile.size / 1024).toFixed(1) }} KB</span>
              </div>
            </div>
            <button class="text-[#717182] hover:text-[#FB2C36]" @click="selectedFile = null; docContent = ''">
              <img :src="apiRowRemove" alt="" class="h-4 w-4" />
            </button>
          </div>

          <div v-else-if="selectedAgent !== 'UI'" class="relative group">
            <textarea 
              v-model="docContent"
              placeholder="粘贴接口文档内容（支持 Markdown / OpenAPI JSON 或 YAML）..."
              class="h-[180px] w-full resize-none rounded-[12px] border border-black/10 bg-white p-4 text-sm leading-relaxed outline-none transition-all focus:border-[#155DFC] focus:ring-4 focus:ring-[#155DFC]/5"
            ></textarea>
            <div class="absolute bottom-3 right-4 flex items-center gap-4 text-[12px]">
              <button class="flex items-center gap-1 text-[#155DFC] hover:underline font-medium" @click="loadExample">
                <span class="text-[14px]">🔗</span> 加载示例
              </button>
              <button class="flex items-center gap-1 text-[#717182] hover:text-[#FB2C36] font-medium" @click="clearContent">
                <img :src="apiRowRemove" alt="" class="h-3.5 w-3.5 opacity-60" /> 清空
              </button>
            </div>
          </div>

          <div v-else class="grid grid-cols-1 gap-3">
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2 text-sm font-bold text-[#0A0A0A]">
                <span class="w-1 h-4 bg-[#155DFC] rounded-full"></span>
                <span>页面标识 pageId</span>
              </div>
              <input
                v-model="uiPageId"
                placeholder="例如：sample-login-page"
                class="h-12 w-full rounded-[12px] border border-black/10 bg-white px-4 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-4 focus:ring-[#155DFC]/5"
              />
            </div>
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2 text-sm font-bold text-[#0A0A0A]">
                <span class="w-1 h-4 bg-[#155DFC] rounded-full"></span>
                <span>Figma 链接（可选）</span>
              </div>
              <input
                v-model="uiFigmaUrl"
                placeholder="https://www.figma.com/..."
                class="h-12 w-full rounded-[12px] border border-black/10 bg-white px-4 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-4 focus:ring-[#155DFC]/5"
              />
            </div>
          </div>

          <!-- Prompt Input -->
          <div class="flex flex-col gap-2 mt-2">
            <div class="flex items-center gap-2 text-sm font-bold text-[#0A0A0A]">
              <span class="w-1 h-4 bg-[#155DFC] rounded-full"></span>
              <span>智能体 Prompt (可选)</span>
            </div>
            <input 
              v-model="instruction"
              placeholder="例如：只生成登录模块的测试用例，包含异常流..."
              class="h-12 w-full rounded-[12px] border border-black/10 bg-white px-4 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-4 focus:ring-[#155DFC]/5"
            />
          </div>

          <div v-if="selectedAgent !== 'UI' && !docContent.trim() && !selectedFile" class="flex items-center gap-2 rounded-[8px] bg-[#F8FAFC] border border-black/5 px-3 py-2 text-xs text-[#64748B]">
            <span class="text-blue-500">ℹ️</span> 请提供文档内容或上传文件
          </div>
          <div v-else-if="selectedAgent === 'UI' && !uiPageId.trim()" class="flex items-center gap-2 rounded-[8px] bg-[#F8FAFC] border border-black/5 px-3 py-2 text-xs text-[#64748B]">
            <span class="text-blue-500">ℹ️</span> 请输入 pageId 后即可执行 UI 测试
          </div>
        </div>

        <div v-if="selectedAgent === 'CASE'" class="rounded-[16px] border border-black/5 bg-white p-5 shadow-sm">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div class="text-sm font-bold text-[#0A0A0A]">用例生成审核流程</div>
              <div class="mt-1 text-[12px] leading-4 text-[#717182]">AI 只生成候选，正式入库必须由你确认。</div>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span
                v-for="(step, index) in caseWorkflowSteps"
                :key="step"
                class="flex h-8 items-center gap-2 rounded-full border border-black/10 bg-[#F8FAFC] px-3 text-[12px] font-medium text-[#475569]"
              >
                <span class="flex h-5 w-5 items-center justify-center rounded-full bg-white text-[11px] text-[#155DFC]">{{ index + 1 }}</span>
                {{ step }}
              </span>
            </div>
          </div>
        </div>

        <!-- Agent Selection Section -->
        <div class="rounded-[16px] border border-black/5 bg-white p-5 shadow-sm">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div class="flex items-center gap-2 text-sm font-bold text-[#0A0A0A]">
                <span class="w-1.5 h-4 bg-[#155DFC] rounded-full"></span>
                <span>智能体类型</span>
              </div>
              <div class="mt-1 text-[12px] leading-4 text-[#717182]">{{ selectedAgentOption.description }}</div>
            </div>
            <select
              v-model="selectedAgent"
              aria-label="智能体类型"
              class="h-10 min-w-[220px] rounded-[10px] border border-black/10 bg-[#F8FAFC] px-3 text-[13px] font-medium text-[#0A0A0A] outline-none focus:border-[#155DFC]"
            >
              <option v-for="item in agentOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="mt-4 flex items-center gap-3 rounded-[10px] bg-[#F8FAFC] px-3 py-3">
            <div class="flex h-9 w-9 items-center justify-center rounded-[10px] bg-[#E0E7FF]">
              <img :src="selectedAgent === 'CASE' ? navCases : navExecution" alt="" class="h-5 w-5" />
            </div>
            <div>
              <div class="text-[13px] font-semibold text-[#0A0A0A]">{{ selectedAgentOption.label }}</div>
              <div class="text-[12px] leading-4 text-[#717182]">下方只展示当前类型需要的配置。</div>
            </div>
          </div>
        </div>

        <!-- Dynamic Form Fields -->
        <div class="flex flex-col gap-5 rounded-[16px] border border-black/5 bg-white p-6 shadow-sm">
          <template v-if="selectedAgent === 'CASE'">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5 text-[13px] font-medium text-[#475569]">
                <span class="text-lg">⌨️</span> 测试框架
              </div>
              <select v-model="testFramework" class="h-9 w-[180px] rounded-[8px] border border-black/10 bg-[#F8FAFC] px-3 text-[13px] font-medium outline-none focus:border-[#155DFC]">
                <option value="pytest + requests">pytest + requests</option>
                <option value="unittest">unittest</option>
              </select>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5 text-[13px] font-medium text-[#475569]">
                <span class="text-lg">ℹ️</span> 断言风格
              </div>
              <span class="text-[13px] text-[#64748B] bg-[#F1F5F9] px-3 py-1 rounded-full font-medium">自动根据响应断言状态码 & 结构</span>
            </div>
          </template>

          <template v-else-if="selectedAgent === 'PERF'">
            <div class="text-[13px] font-semibold leading-5 text-[#0A0A0A]">性能参数</div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5 text-[13px] font-medium text-[#475569]">
                <span class="text-lg">👥</span> 并发用户数
              </div>
              <input v-model.number="perfVus" type="number" class="h-9 w-[100px] rounded-[8px] border border-black/10 bg-[#F8FAFC] px-3 text-[13px] font-bold outline-none focus:border-[#155DFC]" />
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5 text-[13px] font-medium text-[#475569]">
                <span class="text-lg">📈</span> spawn 速率
              </div>
              <input v-model.number="perfSpawnRate" type="number" class="h-9 w-[100px] rounded-[8px] border border-black/10 bg-[#F8FAFC] px-3 text-[13px] font-bold outline-none focus:border-[#155DFC]" />
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5 text-[13px] font-medium text-[#475569]">
                <span class="text-lg">⏳</span> 运行时间(秒)
              </div>
              <input v-model.number="perfDuration" type="number" class="h-9 w-[100px] rounded-[8px] border border-black/10 bg-[#F8FAFC] px-3 text-[13px] font-bold outline-none focus:border-[#155DFC]" />
            </div>
          </template>

          <template v-else>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5 text-[13px] font-medium text-[#475569]">
                <span class="text-lg">🎯</span> 断言等级
              </div>
              <select v-model="uiAssertLevel" class="h-9 w-[120px] rounded-[8px] border border-black/10 bg-[#F8FAFC] px-3 text-[13px] font-medium outline-none focus:border-[#155DFC]">
                <option value="P0">P0</option>
                <option value="P1">P1</option>
                <option value="P2">P2</option>
              </select>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5 text-[13px] font-medium text-[#475569]">
                <span class="text-lg">🖥️</span> 有头执行
              </div>
              <label class="inline-flex cursor-pointer items-center gap-2 text-[13px] font-medium text-[#475569]">
                <input v-model="uiHeaded" type="checkbox" class="h-4 w-4 rounded border-black/20 text-[#155DFC] focus:ring-[#155DFC]" />
                <span>{{ uiHeaded ? '开启' : '关闭' }}</span>
              </label>
            </div>
            <div class="text-[13px] text-[#64748B]">
              将直接调用后端生成并执行接口，完成后可一键跳转报告中心“UI测试报告”。
            </div>
          </template>
        </div>
      </div>

      <!-- Action Button -->
      <div class="mt-6 flex flex-col gap-3">
        <button 
          type="button"
          class="flex h-[52px] w-full items-center justify-center gap-3 rounded-full bg-[#0F172A] text-[16px] font-bold text-white shadow-xl transition-all hover:bg-[#1E293B] active:scale-[0.98] disabled:opacity-50"
          :disabled="!canGenerate || isGenerating"
          @click="handleGenerate"
        >
          <img v-if="isGenerating" :src="runsStatusRunning" alt="" class="h-5 w-5 animate-spin" />
          <img v-else :src="btnAiGenerate" alt="" class="h-5 w-5 brightness-0 invert" />
          <span>{{ selectedAgent === 'CASE' ? '开始生成' : selectedAgent === 'PERF' ? '开始生成' : '生成并执行UI测试' }}</span>
        </button>
        
        <button 
          v-if="selectedAgent === 'CASE'"
          type="button"
          class="flex h-[52px] w-full items-center justify-center gap-3 rounded-full bg-[#155DFC] text-[16px] font-bold text-white shadow-xl transition-all hover:bg-[#1048CB] active:scale-[0.98] disabled:opacity-50"
          :disabled="(!docContent.trim() && !selectedFile) || isGenerating"
          @click="handleGenerate"
        >
          <img v-if="isGenerating" :src="runsStatusRunning" alt="" class="h-5 w-5 animate-spin" />
          <img v-else :src="btnAiGenerate" alt="" class="h-5 w-5 brightness-0 invert" />
          <span>生成候选用例，确认后入库</span>
        </button>

        <button
          v-if="selectedAgent === 'UI' && lastUiRunId"
          type="button"
          class="flex h-[52px] w-full items-center justify-center gap-3 rounded-full bg-[#155DFC] text-[16px] font-bold text-white shadow-xl transition-all hover:bg-[#1048CB] active:scale-[0.98]"
          @click="goToUiReports"
        >
          <span>跳转报告中心（UI测试报告）</span>
        </button>
      </div>
    </div>

    <!-- Right Pane -->
    <div class="flex w-1/2 flex-col bg-[#F5F5F7] p-6 overflow-hidden">
      <div class="flex flex-1 flex-col overflow-hidden rounded-[24px] border border-black/5 bg-[#0F172A] shadow-2xl relative">
        <!-- Code Header -->
        <div class="flex h-[64px] items-center justify-between px-8 border-b border-white/5 bg-white/[0.02]">
          <div class="flex items-center gap-2">
            <div class="flex gap-2">
              <div class="h-3 w-3 rounded-full bg-[#FF5F56]"></div>
              <div class="h-3 w-3 rounded-full bg-[#FFBD2E]"></div>
              <div class="h-3 w-3 rounded-full bg-[#27C93F]"></div>
            </div>
            <span class="ml-6 text-[12px] font-bold text-white/45">生成结果</span>
          </div>

          <div v-if="resultText" class="flex items-center gap-3">
            <button
              v-if="executionResult"
              class="flex items-center gap-2 rounded-full bg-white/5 px-5 py-2 text-[12px] font-bold text-white transition-all hover:bg-white/10 active:scale-95"
              @click="executionResult = ''"
            >
              <span>📄</span> 脚本
            </button>
            <select
              v-model="resultAction"
              aria-label="更多操作"
              class="h-9 rounded-full border border-white/10 bg-white/5 px-4 text-[12px] font-bold text-white outline-none"
            >
              <option v-for="item in resultActionOptions" :key="item.value" :value="item.value" class="text-[#0A0A0A]">
                {{ item.label }}
              </option>
            </select>
            <button
              class="flex items-center gap-2 rounded-full bg-[#155DFC] px-5 py-2 text-[12px] font-bold text-white transition-all hover:bg-[#1048CB] active:scale-95 shadow-lg shadow-[#155DFC]/20"
              :disabled="!canRunResultAction"
              :class="!canRunResultAction ? 'cursor-not-allowed opacity-50 hover:bg-[#155DFC] active:scale-100' : ''"
              @click="runResultAction"
            >
              执行操作
            </button>
          </div>
        </div>

        <!-- Code Viewer Area -->
        <div class="relative flex-1 overflow-auto p-8 font-mono text-[13px] leading-relaxed custom-scrollbar-dark">
          <div v-if="!resultText && !isGenerating" class="flex h-full flex-col items-center justify-center gap-6">
            <div class="text-[48px] filter drop-shadow-2xl">✨</div>
            <div class="flex flex-col items-center gap-2">
              <p class="text-[15px] font-medium text-white/60">已清空文档</p>
              <p class="text-[12px] text-white/30">等待新文档并重新生成</p>
            </div>
          </div>

          <div v-else-if="isGenerating" class="flex h-full flex-col items-center justify-center gap-6">
            <div class="relative">
              <img :src="runsStatusRunning" alt="" class="h-16 w-16 animate-spin opacity-20" />
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-2xl">🤖</span>
              </div>
            </div>
            <p class="text-[14px] font-medium text-white/40 tracking-wide">AI 正在思考并生成中...</p>
          </div>

          <pre v-else class="whitespace-pre-wrap break-all text-[#E2E8F0] selection:bg-[#155DFC]/30">{{ executionResult || resultText }}</pre>
        </div>

        <div v-if="selectedAgent === 'CASE' && resultText" class="border-t border-white/5 bg-white/[0.03] px-8 py-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div class="text-[12px] font-bold text-white/70">去重状态</div>
              <div class="mt-1 text-[12px] leading-4 text-white/40">{{ caseDedupSummary }}</div>
            </div>
            <label class="inline-flex cursor-pointer items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[12px] font-bold text-white/70">
              <input
                v-model="caseReviewConfirmed"
                aria-label="确认已完成去重检查和人工审核"
                type="checkbox"
                class="h-4 w-4 accent-[#155DFC]"
              />
              <span>确认已完成去重检查和人工审核</span>
            </label>
          </div>
        </div>

        <!-- Watermark/Footer -->
        <div class="h-10 border-t border-white/5 bg-white/[0.01] flex items-center px-8 justify-between">
          <span class="text-[10px] text-white/18 font-medium">AI 生成引擎 v1.0</span>
          <span class="text-[10px] text-white/10 font-mono">{{ (executionResult || resultText) ? ((executionResult || resultText).length / 1024).toFixed(2) + ' KB' : '0 KB' }}</span>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <div v-if="showPreviewModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-8">
      <div class="flex h-full w-full max-w-6xl flex-col overflow-hidden rounded-[24px] bg-white shadow-2xl">
        <div class="flex h-16 items-center justify-between border-b border-black/5 px-8">
          <div class="flex items-center gap-3">
            <span class="text-2xl">👁️</span>
            <h3 class="text-lg font-bold text-[#0A0A0A]">预览生成结果: {{ resultFileName }}</h3>
          </div>
          <button class="flex h-10 w-10 items-center justify-center rounded-full hover:bg-black/5 transition-colors" @click="showPreviewModal = false">
            <img :src="apiRowRemove" alt="" class="h-5 w-5 opacity-40" />
          </button>
        </div>
        
        <div class="flex-1 overflow-auto p-8 custom-scrollbar-light">
          <template v-if="selectedAgent === 'CASE'">
            <table class="w-full border-collapse text-left text-[13px]">
              <thead>
                <tr class="border-b border-black/10 bg-[#F8FAFC]">
                  <th class="px-4 py-3 font-bold text-[#475569]">用例标题</th>
                  <th class="px-4 py-3 font-bold text-[#475569]">方法</th>
                  <th class="px-4 py-3 font-bold text-[#475569]">URL</th>
                  <th class="px-4 py-3 font-bold text-[#475569]">预期结果</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in parsedCsv" :key="idx" class="border-b border-black/5 hover:bg-black/[0.02] transition-colors">
                  <td class="px-4 py-3 font-medium text-[#0A0A0A]">{{ row.title }}</td>
                  <td class="px-4 py-3">
                    <span class="rounded px-2 py-0.5 text-[11px] font-bold text-white uppercase" :class="getMethodColor(row.apiMethod)">
                      {{ row.apiMethod }}
                    </span>
                  </td>
                  <td class="px-4 py-3 font-mono text-[#717182]">{{ row.apiUrl }}</td>
                  <td class="px-4 py-3 text-[#717182]">{{ row.expectedResult }}</td>
                </tr>
              </tbody>
            </table>
          </template>
          <template v-else>
            <pre class="rounded-[12px] bg-[#F8FAFC] p-6 font-mono text-[13px] leading-relaxed text-[#1E293B] border border-black/5">{{ resultText }}</pre>
          </template>
        </div>

        <div class="flex h-20 items-center justify-end gap-4 border-t border-black/5 bg-[#F8FAFC] px-8">
          <button class="rounded-full border border-black/10 px-8 py-2.5 text-sm font-bold text-[#475569] transition-all hover:bg-black/5" @click="showPreviewModal = false">关闭</button>
          <button class="rounded-full bg-[#155DFC] px-8 py-2.5 text-sm font-bold text-white transition-all hover:bg-[#1048CB] shadow-lg shadow-[#155DFC]/20" @click="downloadResult">下载并保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Custom Scrollbar for dark theme */
.custom-scrollbar-dark::-webkit-scrollbar {
  width: 8px;
}
.custom-scrollbar-dark::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}
.custom-scrollbar-dark::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.1);
}
.custom-scrollbar-dark::-webkit-scrollbar-track {
  background: transparent;
}

/* Custom Scrollbar for light theme */
.custom-scrollbar-light::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar-light::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 2px;
}
.custom-scrollbar-light::-webkit-scrollbar-track {
  background: transparent;
}

textarea::-webkit-scrollbar {
  width: 4px;
}
textarea::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 2px;
}

/* Animation */
@keyframes pulse-soft {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}
.animate-pulse-soft {
  animation: pulse-soft 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
