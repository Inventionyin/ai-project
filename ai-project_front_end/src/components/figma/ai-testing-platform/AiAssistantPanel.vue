<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  generateDocCsv, 
  generateK6,
  generateAndRunUiTest,
  generatePytestPoFromUrl,
  executeK6,
  importTestcases,
  generateDocAndImport,
  fetchProjectEnvironments,
  type ProjectEnvironment
} from '@/lib/aiTestingPlatformApi'
import navApiCollection from '@/assets/figma/ai-testing-platform/nav-api-collection.svg'
import navCases from '@/assets/figma/ai-testing-platform/nav-cases.svg'
import navExecution from '@/assets/figma/ai-testing-platform/nav-execution.svg'
import runsStatusRunning from '@/assets/figma/ai-testing-platform/runs-status-running.svg'
import btnAiGenerate from '@/assets/figma/ai-testing-platform/btn-ai-generate.svg'
import apiRowRemove from '@/assets/figma/ai-testing-platform/api-row-remove-1.svg'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => String(route.params.projectId || ''))

// Form State
const docContent = ref('')
const selectedFile = ref<File | null>(null)
const instruction = ref('')
const selectedAgent = ref<'CASE' | 'PERF' | 'UI_AUTO'>('CASE')
const testFramework = ref('pytest + requests')
const perfVus = ref(50)
const perfSpawnRate = ref(10)
const perfDuration = ref(60)
const environmentUrl = ref('')
const environments = ref<ProjectEnvironment[]>([])
const uiAutoMode = ref<'RUN' | 'CODEGEN'>('RUN')
const uiPageId = ref('')
const uiPageUrl = ref('')
const uiFigmaUrl = ref('')
const uiAssertLevel = ref<'P0' | 'P1' | 'P2'>('P0')
const uiSuiteType = ref<'smoke' | 'regression'>('smoke')
const uiHeaded = ref(false)
const uiForceRecapture = ref(false)
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

const canGenerate = computed(() => {
  if (selectedAgent.value === 'UI_AUTO') {
    if (uiAutoMode.value === 'RUN') {
      return Boolean(uiPageId.value.trim()) && Boolean(projectId.value)
    }
    return Boolean(uiPageUrl.value.trim()) && Boolean(projectId.value)
  }
  return Boolean(docContent.value.trim() || selectedFile.value)
})

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
  if ((selectedAgent.value === 'CASE' || selectedAgent.value === 'PERF') && !docContent.value.trim() && !selectedFile.value) {
    showToast('请输入接口文档内容或上传文件', 'error')
    return
  }

  isGenerating.value = true
  try {
    if (selectedAgent.value === 'UI_AUTO') {
      if (!projectId.value) {
        showToast('项目 ID 缺失', 'error')
        return
      }
      if (uiAutoMode.value === 'RUN') {
        if (!uiPageId.value.trim()) {
          showToast('请输入 pageId', 'error')
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
          meta: { source: 'ai_assistant_ui_auto_run' }
        })
        lastUiRunId.value = res.runId
        resultFileName.value = `${res.pageId}.spec.ts`
        resultText.value = [
          `[UI自动化测试执行结果 - ${res.status}]`,
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
        showToast('UI自动化测试执行完成')
        return
      }

      if (!uiPageUrl.value.trim()) {
        showToast('请输入 pageUrl', 'error')
        return
      }
      const res = await generatePytestPoFromUrl({
        projectId: projectId.value,
        pageUrl: uiPageUrl.value.trim(),
        pageId: uiPageId.value.trim() || undefined,
        suiteType: uiSuiteType.value,
        assertLevel: uiAssertLevel.value,
        headed: uiHeaded.value,
        forceRecapture: uiForceRecapture.value,
        triggerBy: 'AI_ASSISTANT',
        meta: { source: 'ai_assistant_ui_auto_codegen' }
      })
      resultFileName.value = `${res.pageId}_pytest.py`
      resultText.value = [
        `[UI自动化代码生成成功]`,
        `页面标识: ${res.pageId}`,
        `用例类型: ${res.suiteType}`,
        `断言等级: ${res.assertLevel}`,
        `元素数量: ${res.elementCount}`,
        `----------------------------------------`,
        `生成文件路径:`,
        `- 测试用例: ${res.testPath}`,
        `- PageObject: ${res.pagePath}`,
        `- 定位器配置: ${res.locatorsPath}`,
        `- 采集产物: ${res.captureDir}`,
        `----------------------------------------`,
        `执行口令:`,
        res.commandHint
      ].join('\n')
      executionResult.value = res.commandHint
      showToast('代码生成完成')
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

async function handleGenerateAndImport() {
  if (!docContent.value.trim() && !selectedFile.value) {
    showToast('请输入接口文档内容或上传文件', 'error')
    return
  }
  if (!projectId.value) return

  isGenerating.value = true
  try {
    const file = selectedFile.value || new File([new Blob([docContent.value], { type: 'text/plain' })], 'openapi_doc.yaml')
    const res = await generateDocAndImport({
      projectId: projectId.value,
      file,
      llmMode: llmMode.value,
      caseGenMode: 'AUTO',
      instruction: instruction.value,
      maxCases: 100,
      baseUrl: environmentUrl.value
    })
    showToast(`成功导入 ${res.importedCount} 条用例`)
    resultText.value = `[导入结果]\n已成功导入 ${res.importedCount} 条用例${res.failedCount > 0 ? `，失败 ${res.failedCount} 条` : ''}`
    resultFileName.value = ''
    executionResult.value = ''
  } catch (err) {
    showToast(err instanceof Error ? err.message : '生成或导入失败', 'error')
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
  const isPerf = selectedAgent.value === 'PERF'
  const mimeType = isCase ? 'text/csv' : isPerf ? 'application/javascript' : 'text/plain'
  const defaultExt = isCase ? '.csv' : isPerf ? '.js' : '.txt'
  
  let fileName = resultFileName.value
  if (!fileName) {
    const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14)
    fileName = isCase ? `api_test_cases_${timestamp}.csv` : isPerf ? `k6_script_${timestamp}.js` : `ui_result_${timestamp}.txt`
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
</script>

<template>
  <div class="flex flex-col min-h-screen bg-gradient-to-br from-[#F8FAFC] to-[#EFF6FF]">
    <!-- 顶部导航栏 -->
    <header class="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-100 shadow-sm">
      <div class="max-w-screen-xl mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-r from-[#155DFC] to-[#3B82F6] flex items-center justify-center">
            <span class="text-white font-bold text-sm">AI</span>
          </div>
          <h1 class="text-lg font-bold text-slate-800">AI测试助手</h1>
        </div>
        <div v-if="projectId" class="text-sm text-slate-600">
          项目ID: <span class="font-mono font-medium">{{ projectId }}</span>
        </div>
      </div>
    </header>

    <!-- 主要内容区 -->
    <main class="flex-1 w-full py-6 px-4">
      <div class="max-w-screen-xl mx-auto">
        <!-- 智能体选择 Tab 栏 (修改后的样式) -->
        <div class="mb-6 bg-white rounded-2xl shadow-md border border-slate-100 overflow-hidden">
          <div class="px-6 py-4 border-b border-slate-100">

          </div>
          
          <!-- 重构的 Tab 样式：横向小尺寸 Icon+文字 -->
          <div class="px-4 py-2">
            <div class="flex flex-row gap-1 bg-slate-50 rounded-lg p-1">
              <!-- Case Agent Tab -->
              <div 
                class="flex items-center gap-2 flex-1 justify-center py-2 px-3 rounded-lg cursor-pointer transition-all duration-200"
                :class="selectedAgent === 'CASE' 
                  ? 'bg-[#155DFC] text-white shadow-sm' 
                  : 'hover:bg-slate-100 text-slate-700'"
                @click="selectedAgent = 'CASE'"
              >
                <img :src="navCases" alt="测试用例" class="h-4 w-4" />
                <span class="text-sm font-medium">API测试</span>
              </div>

              <!-- Perf Agent Tab -->
              <div 
                class="flex items-center gap-2 flex-1 justify-center py-2 px-3 rounded-lg cursor-pointer transition-all duration-200"
                :class="selectedAgent === 'PERF' 
                  ? 'bg-[#155DFC] text-white shadow-sm' 
                  : 'hover:bg-slate-100 text-slate-700'"
                @click="selectedAgent = 'PERF'"
              >
                <img :src="navExecution" alt="性能脚本" class="h-4 w-4" />
                <span class="text-sm font-medium">性能脚本</span>
              </div>

              <!-- UI Agent Tab -->
              <div 
                class="flex items-center gap-2 flex-1 justify-center py-2 px-3 rounded-lg cursor-pointer transition-all duration-200"
                :class="selectedAgent === 'UI_AUTO' 
                  ? 'bg-[#155DFC] text-white shadow-sm' 
                  : 'hover:bg-slate-100 text-slate-700'"
                @click="selectedAgent = 'UI_AUTO'"
              >
                <img :src="navExecution" alt="UI测试" class="h-4 w-4" />
                <span class="text-sm font-medium">UI自动化测试</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 配置区域 -->
        <div class="mb-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
          <!-- 左侧配置 -->
          <div class="lg:col-span-7 bg-white rounded-2xl shadow-md border border-slate-100 overflow-hidden">
            <div class="px-6 py-4 border-b border-slate-100 bg-slate-50">
              <h2 class="text-base font-bold text-slate-800 flex items-center gap-2">
                <span class="w-2 h-6 bg-[#155DFC] rounded-full"></span>
                {{ selectedAgent === 'CASE' ? '接口文档配置' : selectedAgent === 'PERF' ? '性能测试配置' : 'UI自动化测试配置' }}
              </h2>
            </div>
            
            <div class="p-6 space-y-6">
              <!-- 文件上传/UI配置 -->
              <div>
                <template v-if="selectedAgent === 'CASE' || selectedAgent === 'PERF'">
                  <label class="flex items-center gap-2 rounded-lg bg-[#E8F0FE] px-4 py-2 text-sm font-medium text-[#155DFC] cursor-pointer hover:bg-[#D8E6FD] transition-all group mb-4 block">
                    <img :src="navApiCollection" alt="" class="h-4 w-4" />
                    <span>上传接口文档</span>
                    <input type="file" class="hidden" @change="onFileChange" accept=".md,.json,.yaml,.yml,.pdf,.docx,.txt" />
                  </label>

                  <div v-if="selectedFile" class="flex items-center justify-between rounded-lg border border-[#155DFC]/20 bg-[#F0F7FF] px-4 py-3 mb-4">
                    <div class="flex items-center gap-3">
                      <span class="text-xl">📄</span>
                      <div class="flex flex-col">
                        <span class="text-sm font-medium text-slate-800">{{ selectedFile.name }}</span>
                        <span class="text-xs text-slate-500">{{ (selectedFile.size / 1024).toFixed(1) }} KB</span>
                      </div>
                    </div>
                    <button class="text-slate-500 hover:text-[#FB2C36] transition-colors" @click="selectedFile = null; docContent = ''">
                      <img :src="apiRowRemove" alt="" class="h-4 w-4" />
                    </button>
                  </div>

                  <div v-else class="relative group mb-4">
                    <textarea 
                      v-model="docContent"
                      placeholder="粘贴接口文档内容（支持OpenAPI/Swagger格式）..."
                      class="h-[140px] w-full resize-none rounded-xl border border-slate-200 bg-white p-4 text-sm leading-relaxed outline-none transition-all focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10"
                    ></textarea>
                    <div class="absolute bottom-3 right-4 flex items-center gap-4 text-xs">
                      <button class="flex items-center gap-1 text-[#155DFC] hover:underline font-medium" @click="loadExample">
                        <span class="text-sm">🔗</span> 加载示例
                      </button>
                      <button class="flex items-center gap-1 text-slate-500 hover:text-[#FB2C36] font-medium" @click="clearContent">
                        <img :src="apiRowRemove" alt="" class="h-4 w-4 opacity-60" /> 清空
                      </button>
                    </div>
                  </div>
                </template>

                <div v-else-if="selectedAgent === 'UI_AUTO'" class="space-y-4">
                  <div class="space-y-2">
                    <label class="text-sm font-medium text-slate-700 block">模式</label>
                    <div class="flex flex-row gap-1 rounded-lg bg-slate-50 p-1 border border-slate-200">
                      <button
                        type="button"
                        class="flex-1 rounded-md px-3 py-2 text-sm font-medium transition-all"
                        :class="uiAutoMode === 'RUN' ? 'bg-[#155DFC] text-white shadow-sm' : 'text-slate-700 hover:bg-slate-100'"
                        @click="uiAutoMode = 'RUN'"
                      >
                        UI验证
                      </button>
                      <button
                        type="button"
                        class="flex-1 rounded-md px-3 py-2 text-sm font-medium transition-all"
                        :class="uiAutoMode === 'CODEGEN' ? 'bg-[#155DFC] text-white shadow-sm' : 'text-slate-700 hover:bg-slate-100'"
                        @click="uiAutoMode = 'CODEGEN'"
                      >
                        代码生成
                      </button>
                    </div>
                  </div>

                  <div v-if="uiAutoMode === 'RUN'" class="space-y-4">
                    <div class="space-y-2">
                      <label class="text-sm font-medium text-slate-700 block">页面标识 pageId <span class="text-red-500">*</span></label>
                      <input
                        v-model="uiPageId"
                        placeholder="例如：sample-login-page"
                        class="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10"
                      />
                    </div>
                    <div class="space-y-2">
                      <label class="text-sm font-medium text-slate-700 block">Figma 链接（可选）</label>
                      <input
                        v-model="uiFigmaUrl"
                        placeholder="https://www.figma.com/..."
                        class="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10"
                      />
                    </div>
                  </div>

                  <div v-else class="space-y-4">
                    <div class="space-y-2">
                      <label class="text-sm font-medium text-slate-700 block">页面地址 URL <span class="text-red-500">*</span></label>
                      <input
                        v-model="uiPageUrl"
                        placeholder="https://example.com/login"
                        class="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10"
                      />
                    </div>
                    <div class="space-y-2">
                      <label class="text-sm font-medium text-slate-700 block">页面标识 pageId（可选）</label>
                      <input
                        v-model="uiPageId"
                        placeholder="不填则根据 URL 自动生成"
                        class="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <!-- 提示信息 -->
              <div v-if="(selectedAgent === 'CASE' || selectedAgent === 'PERF') && !docContent.trim() && !selectedFile" class="flex items-center gap-2 rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-600">
                <span class="text-blue-500 text-lg">ℹ️</span> 请提供接口文档内容或上传文件以生成测试用例/脚本
              </div>
              <div v-else-if="selectedAgent === 'UI_AUTO' && uiAutoMode === 'RUN' && !uiPageId.trim()" class="flex items-center gap-2 rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-600">
                <span class="text-blue-500 text-lg">ℹ️</span> 请输入 pageId 后即可执行 UI 验证
              </div>
              <div v-else-if="selectedAgent === 'UI_AUTO' && uiAutoMode === 'CODEGEN' && !uiPageUrl.trim()" class="flex items-center gap-2 rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-600">
                <span class="text-blue-500 text-lg">ℹ️</span> 请输入页面地址 URL 后即可自动生成 UI 代码
              </div>
            </div>
          </div>

          <!-- 右侧配置 -->
          <div class="lg:col-span-5 bg-white rounded-2xl shadow-md border border-slate-100 overflow-hidden">
            <div class="px-6 py-4 border-b border-slate-100 bg-slate-50">
              <h2 class="text-base font-bold text-slate-800 flex items-center gap-2">
                <span class="w-2 h-6 bg-[#155DFC] rounded-full"></span>
                高级配置
              </h2>
            </div>
            
            <div class="p-6 space-y-6">
              <!-- 环境选择 -->
              <div class="space-y-2">
                <label class="text-sm font-medium text-slate-700 block">测试环境 <span class="text-red-500">*</span></label>
                <div class="flex gap-3">
                  <select 
                    v-model="environmentUrl" 
                    class="h-12 flex-1 appearance-none rounded-xl border border-slate-200 bg-white px-4 pr-8 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10 bg-[url('data:image/svg+xml;charset=UTF-8,%3csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27%2364748b%27 stroke-width=%272%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3e%3cpolyline points=%276 9 12 15 18 9%27%3e%3c/polyline%3e%3c/svg%3e')] bg-no-repeat bg-right-4 center bg-contain bg-[length:16px]"
                  >
                    <option value="http://localhost:5173">本地环境</option>
                    <option v-for="env in environments" :key="env.id" :value="env.baseUrl">
                      {{ env.name }}
                    </option>
                    <option v-if="environmentUrl && !['http://localhost:5173', ...environments.map(e => e.baseUrl)].includes(environmentUrl)" :value="environmentUrl">
                      自定义
                    </option>
                  </select>
                </div>
              </div>

              <!-- Prompt Input -->
              <div class="space-y-2">
                <label class="text-sm font-medium text-slate-700 block">智能体提示词（可选）</label>
                <input 
                  v-model="instruction"
                  placeholder="例如：只生成登录模块的测试用例，包含异常场景..."
                  class="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm outline-none transition-all focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10"
                />
              </div>

              <!-- 动态配置项 -->
              <div class="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-4">
                <template v-if="selectedAgent === 'CASE'">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2 text-sm font-medium text-slate-700">
                      <span class="text-lg">⌨️</span> 测试框架
                    </div>
                    <select v-model="testFramework" class="h-10 w-[140px] rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10">
                      <option value="pytest + requests">pytest + requests</option>
                      <option value="unittest">unittest</option>
                    </select>
                  </div>
                </template>

                <template v-else-if="selectedAgent === 'PERF'">
                  <div class="grid grid-cols-3 gap-4">
                    <div class="space-y-2">
                      <label class="text-xs font-medium text-slate-600 block">并发用户数</label>
                      <input v-model.number="perfVus" type="number" min="1" class="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium outline-none focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10" />
                    </div>
                    <div class="space-y-2">
                      <label class="text-xs font-medium text-slate-600 block">生成速率</label>
                      <input v-model.number="perfSpawnRate" type="number" min="1" class="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium outline-none focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10" />
                    </div>
                    <div class="space-y-2">
                      <label class="text-xs font-medium text-slate-600 block">测试时长(秒)</label>
                      <input v-model.number="perfDuration" type="number" min="1" class="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium outline-none focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10" />
                    </div>
                  </div>
                </template>

                <template v-else-if="selectedAgent === 'UI_AUTO'">
                  <div class="space-y-4">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-2 text-sm font-medium text-slate-700">
                        <span class="text-lg">🎯</span> 断言等级
                      </div>
                      <select v-model="uiAssertLevel" class="h-10 w-[100px] rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10">
                        <option value="P0">P0 (核心)</option>
                        <option value="P1">P1 (重要)</option>
                        <option value="P2">P2 (一般)</option>
                      </select>
                    </div>
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-2 text-sm font-medium text-slate-700">
                        <span class="text-lg">🖥️</span> 有头执行
                      </div>
                      <label class="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-700">
                        <div class="relative">
                          <input v-model="uiHeaded" type="checkbox" class="sr-only peer" />
                          <div class="w-12 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#155DFC]"></div>
                        </div>
                        <span>{{ uiHeaded ? '开启' : '关闭' }}</span>
                      </label>
                    </div>

                    <template v-if="uiAutoMode === 'CODEGEN'">
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2 text-sm font-medium text-slate-700">
                          <span class="text-lg">📁</span> 用例类型
                        </div>
                        <select v-model="uiSuiteType" class="h-10 w-[120px] rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-[#155DFC] focus:ring-2 focus:ring-[#155DFC]/10">
                          <option value="smoke">冒烟测试</option>
                          <option value="regression">回归测试</option>
                        </select>
                      </div>
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2 text-sm font-medium text-slate-700">
                          <span class="text-lg">🔄</span> 强制重抓
                        </div>
                        <label class="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-700">
                          <div class="relative">
                            <input v-model="uiForceRecapture" type="checkbox" class="sr-only peer" />
                            <div class="w-12 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#155DFC]"></div>
                          </div>
                          <span>{{ uiForceRecapture ? '开启' : '关闭' }}</span>
                        </label>
                      </div>
                    </template>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="mb-6 flex flex-wrap gap-4 justify-center lg:justify-start">
          <button 
            type="button"
            class="flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-[#0F172A] to-[#1E293B] text-white font-bold py-3 px-8 shadow-lg transition-all hover:shadow-xl active:scale-95 disabled:opacity-50 disabled:pointer-events-none disabled:shadow-none min-w-[180px]"
            :disabled="!canGenerate || isGenerating"
            @click="handleGenerate"
          >
            <img v-if="isGenerating" :src="runsStatusRunning" alt="" class="h-5 w-5 animate-spin" />
            <img v-else :src="btnAiGenerate" alt="" class="h-5 w-5 brightness-0 invert" />
            <span>{{ selectedAgent === 'CASE' ? '仅生成预览' : selectedAgent === 'PERF' ? '立即生成' : uiAutoMode === 'RUN' ? '生成并执行UI自动化测试' : '立即生成UI自动化代码' }}</span>
          </button>
          
          <button 
            v-if="selectedAgent === 'CASE'"
            type="button"
            class="flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-[#155DFC] to-[#3B82F6] text-white font-bold py-3 px-8 shadow-lg transition-all hover:shadow-xl active:scale-95 disabled:opacity-50 disabled:pointer-events-none disabled:shadow-none min-w-[180px]"
            :disabled="(!docContent.trim() && !selectedFile) || isGenerating"
            @click="handleGenerateAndImport"
          >
            <img v-if="isGenerating" :src="runsStatusRunning" alt="" class="h-5 w-5 animate-spin" />
            <img v-else :src="btnAiGenerate" alt="" class="h-5 w-5 brightness-0 invert" />
            <span>生成并导入</span>
          </button>

          <button
            v-if="selectedAgent === 'UI_AUTO' && lastUiRunId"
            type="button"
            class="flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-[#155DFC] to-[#3B82F6] text-white font-bold py-3 px-8 shadow-lg transition-all hover:shadow-xl active:scale-95 min-w-[180px]"
            @click="goToUiReports"
          >
            <span>📊 查看测试报告</span>
          </button>
        </div>

        <!-- 结果展示区 -->
        <div class="bg-white rounded-2xl shadow-md border border-slate-100 overflow-hidden">
          <div class="px-6 py-4 border-b border-slate-800/10 bg-gradient-to-r from-[#0F172A] to-[#1E293B]">
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <span class="w-2 h-6 bg-[#155DFC] rounded-full"></span>
              生成结果
            </h2>
          </div>
          
          <!-- 结果头部 -->
          <div class="flex h-14 items-center justify-between px-6 border-b border-slate-800/10 bg-slate-900">
            <div class="flex items-center gap-3">
              <div class="flex gap-2">
                <div class="h-3 w-3 rounded-full bg-[#FF5F56]"></div>
                <div class="h-3 w-3 rounded-full bg-[#FFBD2E]"></div>
                <div class="h-3 w-3 rounded-full bg-[#27C93F]"></div>
              </div>
              <span class="ml-4 text-xs font-bold tracking-widest text-white/50 uppercase">Generation Result</span>
            </div>

            <div v-if="resultText" class="flex items-center gap-3">
              <button 
                v-if="executionResult"
                class="flex items-center gap-1 rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white transition-all hover:bg-white/20 active:scale-95"
                @click="executionResult = ''"
              >
                <span>📄</span> 脚本
              </button>
              <button 
                class="flex items-center gap-1 rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white transition-all hover:bg-white/20 active:scale-95" 
                @click="showPreviewModal = true"
              >
                <span>👁️</span> 预览
              </button>
              <button class="flex items-center gap-1 rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white transition-all hover:bg-white/20 active:scale-95" @click="copyResult">
                <span>📋</span> 复制
              </button>
              <button class="flex items-center gap-1 rounded-full bg-[#155DFC] px-3 py-1.5 text-xs font-medium text-white transition-all hover:bg-[#1048CB] active:scale-95 shadow-lg shadow-[#155DFC]/20" @click="downloadResult">
                <span>📥</span> 下载
              </button>
              <button 
                v-if="selectedAgent === 'PERF'"
                class="flex items-center gap-1 rounded-full bg-[#27C93F] px-3 py-1.5 text-xs font-medium text-white transition-all hover:bg-[#1EA835] active:scale-95 shadow-lg shadow-[#27C93F]/20"
                @click="handleExecute"
              >
                <span>⚡</span> 执行
              </button>
              <button 
                v-if="selectedAgent === 'CASE' && resultText && !resultText.includes('[导入结果]')"
                class="flex items-center gap-1 rounded-full bg-[#155DFC] px-3 py-1.5 text-xs font-medium text-white transition-all hover:bg-[#1048CB] active:scale-95 shadow-lg shadow-[#155DFC]/20"
                @click="handleImport"
              >
                <span>📥</span> 导入
              </button>
            </div>
          </div>

          <!-- 结果内容 -->
          <div class="relative bg-slate-900 text-slate-200 font-mono text-sm leading-relaxed p-6 h-[400px] overflow-auto custom-scrollbar-dark">
            <div v-if="!resultText && !isGenerating" class="flex h-full flex-col items-center justify-center gap-6 text-center">
              <div class="text-5xl filter drop-shadow-2xl">✨</div>
              <div class="flex flex-col items-center gap-2">
                <p class="text-base font-medium text-white/70">准备就绪</p>
                <p class="text-sm text-white/40">配置完成后点击生成按钮开始创建测试用例/脚本</p>
              </div>
            </div>

            <div v-else-if="isGenerating" class="flex h-full flex-col items-center justify-center gap-6">
              <div class="relative">
                <img :src="runsStatusRunning" alt="" class="h-16 w-16 animate-spin opacity-20" />
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-3xl">🤖</span>
                </div>
              </div>
              <p class="text-base font-medium text-white/60 tracking-wide">AI 正在思考并生成中...</p>
            </div>

            <pre v-else class="whitespace-pre-wrap break-all text-[#E2E8F0] selection:bg-[#155DFC]/30">{{ executionResult || resultText }}</pre>
          </div>

          <!-- 结果底部 -->
          <div class="h-10 border-t border-slate-800/20 bg-slate-800 flex items-center px-6 justify-between">
            <span class="text-xs text-white/30 font-medium uppercase tracking-tighter">AI Powered Generation Engine v1.0</span>
            <span class="text-xs text-white/30 font-mono">{{ (executionResult || resultText) ? ((executionResult || resultText).length / 1024).toFixed(2) + ' KB' : '0 KB' }}</span>
          </div>
        </div>
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="bg-white border-t border-slate-200 py-4">
      <div class="max-w-screen-xl mx-auto px-4 text-center text-sm text-slate-500">
        AI测试助手 © {{ new Date().getFullYear() }} | 自动化测试解决方案
      </div>
    </footer>

    <!-- Preview Modal -->
    <div v-if="showPreviewModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-6">
      <div class="flex h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div class="flex h-16 items-center justify-between border-b border-slate-200 px-6 bg-slate-50">
          <h3 class="text-base font-bold text-slate-800">生成结果预览</h3>
          <button class="text-slate-500 hover:text-slate-800 transition-colors" @click="showPreviewModal = false">
            <span class="text-xl">✕</span>
          </button>
        </div>
        <div class="flex-1 overflow-auto p-6 bg-slate-900 text-slate-200 font-mono text-sm">
          <pre class="whitespace-pre-wrap break-all">{{ resultText }}</pre>
        </div>
        <div class="border-t border-slate-800/20 bg-slate-800 p-4 flex justify-end gap-3">
          <button class="px-4 py-2 rounded-lg bg-white/10 text-white text-sm font-medium hover:bg-white/20 transition-colors" @click="showPreviewModal = false">
            关闭
          </button>
          <button class="px-4 py-2 rounded-lg bg-[#155DFC] text-white text-sm font-medium hover:bg-[#1048CB] transition-colors" @click="copyResult; showPreviewModal = false">
            复制并关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
