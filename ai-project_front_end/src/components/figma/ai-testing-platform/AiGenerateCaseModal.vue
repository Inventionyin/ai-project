<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import modalCreateIcon from '@/assets/figma/ai-testing-platform/modal-create-icon.svg'
import modalClose28 from '@/assets/figma/ai-testing-platform/modal-close-28.svg'
import filterChevron from '@/assets/figma/ai-testing-platform/filter-chevron.svg'
import { generateDocAndImport, generateDocCsv, previewDocIngest, type DocIngestApiCandidate } from '@/lib/aiTestingPlatformApi'

type SourceType = 'prd' | 'figma' | 'html'
type DedupStrategy = 'STRICT' | 'MERGE' | 'NONE'
type CasePriority = 'P0' | 'P1' | 'P2' | 'P3'
type CaseType = 'API' | 'UI' | 'PERF' | 'MIX'

const props = defineProps<{
  isOpen: boolean
  projectId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'imported', data: { importedCount: number; failedCount: number }): void
}>()

const formData = reactive({
  source: 'prd' as SourceType,
  figmaUrl: '',
  maxCount: 20,
  dedupStrategy: 'STRICT' as DedupStrategy,
  defaultPriority: 'P1' as CasePriority,
  defaultType: 'API' as CaseType,
  useAiCaseGen: true,
  instruction: ''
})

const dedupOptions: Array<{ label: string; value: DedupStrategy }> = [
  { label: '严格去重', value: 'STRICT' },
  { label: '智能合并', value: 'MERGE' },
  { label: '不去重', value: 'NONE' }
]

const priorityOptions: CasePriority[] = ['P0', 'P1', 'P2', 'P3']
const typeOptions: CaseType[] = ['API', 'UI', 'PERF', 'MIX']
const selectedFileName = ref('')
const selectedFileRef = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const currentStep = ref<1 | 2 | 3>(1)
const progressPercent = ref(0)
const generatedCount = ref(0)
const dedupRemovedCount = ref(0)
const lowConfidenceCount = ref(0)
const isImporting = ref(false)
const isDownloading = ref(false)
let progressTimer = 0

type PreviewCase = {
  id: string
  title: string
  description: string
  feature: string
  story: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  url: string
  caseType: CaseType
  priority: CasePriority
  confidence: number
}

const previewCases = ref<PreviewCase[]>([])
const selectedCaseIds = ref<string[]>([])

const selectedSourceSubText = computed(() => {
  if (formData.source === 'prd') return '.md / .docx / .pdf'
  if (formData.source === 'figma') return '粘贴 Figma URL'
  return '.html / .htm'
})

const acceptFileTypes = computed(() => {
  if (formData.source === 'prd') return '.md,.docx,.pdf'
  if (formData.source === 'html') return '.html,.htm'
  return ''
})

function closeModal() {
  window.clearInterval(progressTimer)
  emit('close')
}

function stepClass(step: 1 | 2 | 3) {
  if (step < currentStep.value) return 'bg-[#155DFC] text-white'
  if (step === currentStep.value) return 'bg-[#155DFC] text-white shadow-[0_0_0_4px_#DBEAFE]'
  return 'bg-black/10 text-[#717182]'
}

function stepTextClass(step: 1 | 2 | 3) {
  if (step <= currentStep.value) return 'text-[#0A0A0A]'
  return 'text-[#717182]'
}

function sourceButtonClass(value: SourceType) {
  if (formData.source === value) {
    return 'bg-[#EFF6FF] border-[#2B7FFF] border-[2px] text-[#1447E6]'
  }
  return 'bg-white border-black/10 border-[2px] text-[#717182]'
}

function onSourceChange(value: SourceType) {
  formData.source = value
  selectedFileName.value = ''
}

function openFilePicker() {
  fileInputRef.value?.click()
}

function isValidFileBySource(fileName: string) {
  const lower = fileName.toLowerCase()
  if (formData.source === 'prd') {
    return lower.endsWith('.md') || lower.endsWith('.docx') || lower.endsWith('.pdf')
  }
  if (formData.source === 'html') {
    return lower.endsWith('.html') || lower.endsWith('.htm')
  }
  return false
}

function onSelectFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!isValidFileBySource(file.name)) {
    input.value = ''
    selectedFileName.value = ''
    selectedFileRef.value = null
    window.alert(`文件格式不支持，请上传 ${selectedSourceSubText.value} 文件`)
    return
  }
  selectedFileName.value = file.name
  selectedFileRef.value = file
}

const canStartGeneration = computed(() => {
  if (formData.source === 'figma') return Boolean(formData.figmaUrl.trim())
  return Boolean(selectedFileName.value)
})

const progressWidth = computed(() => `${Math.min(100, Math.max(0, progressPercent.value))}%`)

function showToast(message: string, type: 'success' | 'error' = 'success') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }))
}

function resetGenerationView() {
  currentStep.value = 1
  progressPercent.value = 0
  generatedCount.value = 0
  dedupRemovedCount.value = 0
  lowConfidenceCount.value = 0
  previewCases.value = []
  selectedCaseIds.value = []
  window.clearInterval(progressTimer)
}

function _normalizeMethod(v: unknown): PreviewCase['method'] {
  const m = String(v || '').trim().toUpperCase()
  if (m === 'POST' || m === 'PUT' || m === 'DELETE') return m
  return 'GET'
}

function _normalizeUrl(v: unknown) {
  const u = String(v || '').trim()
  return u || '/unknown'
}

function _normalizeTitle(c: DocIngestApiCandidate) {
  const name = String(c?.name || '').trim()
  if (name) return name.slice(0, 100)
  return `${_normalizeMethod(c?.method)} ${_normalizeUrl(c?.url)}`.slice(0, 100)
}

function _normalizeFeature(c: DocIngestApiCandidate) {
  const f = String(c?.feature || '').trim()
  return f ? f.slice(0, 128) : 'DEFAULT'
}

function _normalizeDescription(c: DocIngestApiCandidate) {
  const t = String(c?.expectedResult || '').trim()
  return t ? t.slice(0, 80) : ''
}

function _confidencePercent(v: unknown) {
  const n = typeof v === 'number' ? v : Number(v)
  if (!Number.isFinite(n)) return 0
  if (n > 1) return Math.max(0, Math.min(100, Math.round(n)))
  return Math.max(0, Math.min(100, Math.round(n * 100)))
}

function _dedupeKey(item: PreviewCase) {
  return `${item.method}::${item.url}::${item.title}`.toLowerCase()
}

function _applyDedup(items: PreviewCase[], strategy: DedupStrategy) {
  if (strategy === 'NONE') {
    return { items, removedCount: 0 }
  }
  const next: PreviewCase[] = []
  const seen = new Set<string>()
  let removedCount = 0
  for (const item of items) {
    const key = _dedupeKey(item)
    if (seen.has(key)) {
      removedCount += 1
      continue
    }
    seen.add(key)
    next.push(item)
  }
  return { items: next, removedCount }
}

async function handleStart() {
  if (formData.source === 'figma' && !formData.figmaUrl.trim()) {
    window.alert('请输入 Figma 链接')
    return
  }
  if (formData.source !== 'figma' && !selectedFileName.value) {
    window.alert(`请上传 ${selectedSourceSubText.value} 文件`)
    return
  }
  if (formData.source === 'figma') {
    window.alert('暂不支持 Figma 源，请先使用文档文件')
    return
  }
  const file = selectedFileRef.value
  if (!file) {
    window.alert('请选择文件')
    return
  }

  resetGenerationView()
  currentStep.value = 2
  progressTimer = window.setInterval(() => {
    if (progressPercent.value >= 95) return
    progressPercent.value = Math.min(95, progressPercent.value + 5)
  }, 120)

  try {
    const instruction = String(formData.instruction || '').trim()
    const llmMode = instruction ? 'AUTO' : 'OFF'
    const parsed = await previewDocIngest({ file, llmMode, instruction })
    const rawCandidates = Array.isArray(parsed?.apiCandidates) ? parsed.apiCandidates : []
    const maxCount = Math.max(1, Number(formData.maxCount) || 1)
    const limited = rawCandidates.slice(0, maxCount)
    const mapped: PreviewCase[] = limited
      .filter((c) => c && typeof c.id === 'string' && c.id.trim())
      .map((c) => ({
        id: c.id,
        title: _normalizeTitle(c),
        description: _normalizeDescription(c),
        feature: _normalizeFeature(c),
        story: '',
        method: _normalizeMethod(c.method),
        url: _normalizeUrl(c.url),
        caseType: formData.defaultType,
        priority: formData.defaultPriority,
        confidence: _confidencePercent(c.confidence)
      }))

    const deduped = _applyDedup(mapped, formData.dedupStrategy)
    previewCases.value = deduped.items
    selectedCaseIds.value = deduped.items.map((item) => item.id)
    generatedCount.value = deduped.items.length
    dedupRemovedCount.value = deduped.removedCount
    lowConfidenceCount.value = deduped.items.filter((item) => item.confidence > 0 && item.confidence < 90).length

    window.clearInterval(progressTimer)
    progressPercent.value = 100
    currentStep.value = 3
  } catch (error) {
    window.clearInterval(progressTimer)
    progressPercent.value = 0
    currentStep.value = 1
    const message = error instanceof Error ? error.message : '生成失败'
    showToast(message, 'error')
  }
}

const allSelected = computed(() => previewCases.value.length > 0 && selectedCaseIds.value.length === previewCases.value.length)
const selectedCount = computed(() => selectedCaseIds.value.length)

function toggleSelectAll(checked: boolean) {
  selectedCaseIds.value = checked ? previewCases.value.map((item) => item.id) : []
}

function toggleCaseSelected(id: string, checked: boolean) {
  if (checked) {
    if (!selectedCaseIds.value.includes(id)) {
      selectedCaseIds.value = [...selectedCaseIds.value, id]
    }
    return
  }
  selectedCaseIds.value = selectedCaseIds.value.filter((item) => item !== id)
}

function removePreviewCase(id: string) {
  previewCases.value = previewCases.value.filter((item) => item.id !== id)
  selectedCaseIds.value = selectedCaseIds.value.filter((item) => item !== id)
}

function confidenceTextClass(value: number) {
  if (value >= 95) return 'text-[#00A63E]'
  if (value >= 90) return 'text-[#D08700]'
  return 'text-[#FF6900]'
}

function regenerateCases() {
  currentStep.value = 1
}

function _resolveCaseGenMode() {
  return formData.useAiCaseGen ? 'AUTO' : 'OFF'
}

function _resolveMaxCases() {
  const n = Math.max(1, Number(formData.maxCount) || 1)
  return Math.min(2000, n * 10)
}

async function downloadCsv() {
  if (isDownloading.value) return
  const file = selectedFileRef.value
  if (!file) return
  const candidateIds = selectedCaseIds.value.slice()
  if (candidateIds.length === 0) return
  isDownloading.value = true
  try {
    const instruction = String(formData.instruction || '').trim()
    const llmMode = instruction ? 'AUTO' : 'OFF'
    const res = await generateDocCsv({
      file,
      llmMode,
      instruction,
      candidateIds,
      caseGenMode: _resolveCaseGenMode(),
      skillId: 'api-doc-test-generator',
      maxCases: _resolveMaxCases()
    })
    const blob = new Blob([res.csvText], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = res.fileName || 'api_test_cases.csv'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    showToast('CSV 已下载')
  } catch (error) {
    const message = error instanceof Error ? error.message : '下载失败'
    showToast(message, 'error')
  } finally {
    isDownloading.value = false
  }
}

async function importCases() {
  if (isImporting.value) return
  const projectId = String(props.projectId || '').trim()
  if (!projectId) return
  const file = selectedFileRef.value
  if (!file) return
  const candidateIds = selectedCaseIds.value.slice()
  isImporting.value = true
  try {
    const instruction = String(formData.instruction || '').trim()
    const llmMode = instruction ? 'AUTO' : 'OFF'
    const data = await generateDocAndImport({
      projectId,
      file,
      mode: 'partial',
      llmMode,
      candidateIds,
      instruction,
      caseGenMode: _resolveCaseGenMode(),
      skillId: 'api-doc-test-generator',
      maxCases: _resolveMaxCases()
    })
    emit('imported', { importedCount: data.importedCount, failedCount: data.failedCount })
    closeModal()
  } catch (error) {
    const message = error instanceof Error ? error.message : '入库失败'
    showToast(message, 'error')
  } finally {
    isImporting.value = false
  }
}

watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetGenerationView()
  } else {
    window.clearInterval(progressTimer)
  }
})
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeModal">
    <div class="relative h-[calc(100vh-32px)] w-[calc(100vw-32px)] max-w-[640px] overflow-hidden rounded-[16px] bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:h-[483.59px]">
      <div class="flex h-[74.67px] items-center justify-between border-b border-black/10 px-[24px]">
        <div class="flex items-center gap-[10px]">
          <div class="flex h-[32px] w-[32px] items-center justify-center rounded-[10px] bg-[#155DFC]">
            <img :src="modalCreateIcon" alt="" class="h-[16px] w-[16px]" />
          </div>
          <div class="flex flex-col gap-[2px]">
            <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">AI 生成用例</div>
            <div class="text-[12px] leading-[16px] text-[#717182]">基于文档自动提取并生成测试用例</div>
          </div>
        </div>
        <button type="button" class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px]" @click="closeModal">
          <img :src="modalClose28" alt="" class="h-[28px] w-[28px]" />
        </button>
      </div>

      <div class="flex h-[340px] flex-col gap-[24px] overflow-auto px-[24px] py-[24px]">
        <div class="flex items-center">
          <div class="flex items-center gap-[12px]">
            <span class="flex h-[24px] w-[24px] items-center justify-center rounded-full text-[12px] font-semibold" :class="stepClass(1)">1</span>
            <span class="text-[12px] font-medium leading-[16px]" :class="stepTextClass(1)">配置参数</span>
          </div>
          <div class="mx-[10px] h-[1px] w-[40px]" :class="currentStep === 2 ? 'bg-[#155DFC]' : 'bg-black/10'" />
          <div class="flex items-center gap-[12px]">
            <span class="flex h-[24px] w-[24px] items-center justify-center rounded-full text-[12px] font-semibold" :class="stepClass(2)">2</span>
            <span class="text-[12px] font-medium leading-[16px]" :class="stepTextClass(2)">生成中</span>
          </div>
          <div class="mx-[10px] h-[1px] w-[40px] bg-black/10" />
          <div class="flex items-center gap-[12px]">
            <span class="flex h-[24px] w-[24px] items-center justify-center rounded-full text-[12px] font-semibold" :class="stepClass(3)">3</span>
            <span class="text-[12px] font-medium leading-[16px]" :class="stepTextClass(3)">预览入库</span>
          </div>
        </div>

        <div v-if="currentStep === 1" class="flex flex-col gap-[20px]">
          <div class="flex flex-col gap-[8px]">
            <div class="text-[12px] font-semibold leading-[16px] text-[#0A0A0A]">文档来源 <span class="text-[#FB2C36]">*</span></div>
            <div class="grid grid-cols-1 gap-[12px] sm:grid-cols-3">
              <button type="button" class="flex h-[89px] flex-col items-center justify-center gap-[6px] rounded-[14px]" :class="sourceButtonClass('prd')" @click="onSourceChange('prd')">
                <span class="text-[12px] font-medium leading-[16px]">PRD 文档</span>
                <span class="text-[10px] leading-[15px] opacity-70">{{ formData.source === 'prd' ? '.md / .docx / .pdf' : '.md / .docx / .pdf' }}</span>
              </button>
              <button type="button" class="flex h-[89px] flex-col items-center justify-center gap-[6px] rounded-[14px]" :class="sourceButtonClass('figma')" @click="onSourceChange('figma')">
                <span class="text-[12px] font-medium leading-[16px]">Figma 链接</span>
                <span class="text-[10px] leading-[15px] opacity-70">粘贴 Figma URL</span>
              </button>
              <button type="button" class="flex h-[89px] flex-col items-center justify-center gap-[6px] rounded-[14px]" :class="sourceButtonClass('html')" @click="onSourceChange('html')">
                <span class="text-[12px] font-medium leading-[16px]">HTML 文档</span>
                <span class="text-[10px] leading-[15px] opacity-70">.html / .htm</span>
              </button>
            </div>
          </div>

          <div v-if="formData.source === 'figma'" class="flex flex-col gap-[6px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">Figma 链接 <span class="text-[#FB2C36]">*</span></div>
            <input
              v-model="formData.figmaUrl"
              type="text"
              placeholder="https://www.figma.com/file/..."
              class="h-[52px] rounded-[10px] border border-black/10 px-[16px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              style="font-family: Consolas"
            />
          </div>

          <div v-else class="flex flex-col gap-[6px]">
            <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">上传文件 <span class="text-[#FB2C36]">*</span></div>
            <button type="button" class="flex h-[80px] items-center gap-[12px] rounded-[14px] border-[2px] border-dashed border-black/10 pl-[16px] text-left" @click="openFilePicker">
              <div class="flex h-[18px] w-[18px] items-center justify-center rounded-[4px] bg-[#ECECF0] text-[12px] text-[#717182]">↑</div>
              <div class="flex flex-col gap-[2px]">
                <span class="text-[14px] leading-[20px] text-[#717182]">{{ selectedFileName || '点击选择或拖拽文件至此' }}</span>
                <span class="text-[12px] leading-[16px] text-[#717182]">支持 {{ selectedSourceSubText }}</span>
              </div>
            </button>
            <input ref="fileInputRef" type="file" class="hidden" :accept="acceptFileTypes" @change="onSelectFile" />
          </div>

          <div class="grid grid-cols-1 gap-x-[16px] gap-y-[16px] sm:grid-cols-2">
            <div class="flex flex-col gap-[6px]">
              <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">最多生成条数</div>
              <input v-model.number="formData.maxCount" type="number" min="1" class="h-[36px] rounded-[10px] border border-black/10 px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none" />
            </div>
            <div class="flex flex-col gap-[6px]">
              <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">去重策略</div>
              <select v-model="formData.dedupStrategy" class="h-[36px] rounded-[10px] border border-black/10 px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none">
                <option v-for="item in dedupOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-[6px]">
              <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">默认优先级</div>
              <select v-model="formData.defaultPriority" class="h-[36px] rounded-[10px] border border-black/10 px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none">
                <option v-for="item in priorityOptions" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-[6px]">
              <div class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">默认类型</div>
              <select v-model="formData.defaultType" class="h-[36px] rounded-[10px] border border-black/10 px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none">
                <option v-for="item in typeOptions" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
          </div>

          <div class="flex flex-col gap-[12px]">
            <div class="text-[12px] font-semibold leading-[16px] text-[#0A0A0A]">指令</div>
            <div class="flex flex-col gap-[6px]">
              <textarea
                v-model="formData.instruction"
                rows="3"
                placeholder="例如：根据接口文档生成测试用例；只生成“用户/登录”模块；输出 CSV"
                class="w-full resize-none rounded-[10px] border border-black/10 px-[16px] py-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              />
              <div class="text-[12px] leading-[16px] text-[#717182]">
                触发示例：根据接口文档生成测试用例 / 把 API.md 转成测试用例 / 生成登录模块的接口文档
              </div>
            </div>
          </div>

          <label class="flex items-center gap-[8px] text-[12px] leading-[16px] text-[#0A0A0A]">
            <input v-model="formData.useAiCaseGen" type="checkbox" class="h-[14px] w-[14px]" />
            使用大模型生成测试用例（按 CSV 模板）
          </label>
        </div>
 
        <div v-else-if="currentStep === 2" class="relative flex h-full flex-col items-center">
          <div class="relative mt-[24px] h-[80px] w-[80px]">
            <div class="absolute -left-[28.15px] -top-[28.15px] h-[136.3px] w-[136.3px] rounded-full bg-[#DBEAFE] opacity-[0.118484]" />
            <div class="relative flex h-[80px] w-[80px] items-center justify-center rounded-full bg-[#155DFC]">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M26.6668 8L12.0002 22.6667L5.3335 16" stroke="white" stroke-width="2.66667" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
          </div>
          <div class="mt-[24px] text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">生成中...</div>
          <div class="mt-[4px] text-[12px] leading-[16px] text-[#717182]">请稍候，这通常需要 10-30 秒</div>

          <div class="mt-[24px] w-full max-w-[384px]">
            <div class="flex items-center justify-between text-[12px] leading-[16px] text-[#717182]">
              <span>进度</span>
              <span>{{ progressPercent }}%</span>
            </div>
            <div class="mt-[6px] h-[8px] w-full overflow-hidden rounded-full bg-[#ECECF0]">
              <div class="h-full rounded-full bg-[#155DFC] transition-all duration-200" :style="{ width: progressWidth }" />
            </div>
          </div>

          <div class="mt-[24px] grid w-full max-w-[384px] grid-cols-3 gap-[16px]">
            <div class="rounded-[14px] border border-black/10 bg-[rgba(236,236,240,0.4)] px-[12px] pb-[1px] pt-[12px] text-center">
              <div class="text-[20px] font-semibold leading-[28px] text-[#155DFC]">{{ generatedCount }}</div>
              <div class="text-[12px] leading-[16px] text-[#717182]">已生成</div>
            </div>
            <div class="rounded-[14px] border border-black/10 bg-[rgba(236,236,240,0.4)] px-[12px] pb-[1px] pt-[12px] text-center">
              <div class="text-[20px] font-semibold leading-[28px] text-[#D08700]">{{ dedupRemovedCount }}</div>
              <div class="text-[12px] leading-[16px] text-[#717182]">去重移除</div>
            </div>
            <div class="rounded-[14px] border border-black/10 bg-[rgba(236,236,240,0.4)] px-[12px] pb-[1px] pt-[12px] text-center">
              <div class="text-[20px] font-semibold leading-[28px] text-[#FF6900]">{{ lowConfidenceCount }}</div>
              <div class="text-[12px] leading-[16px] text-[#717182]">低置信度</div>
            </div>
          </div>
        </div>

        <div v-else class="flex flex-col gap-[16px]">
          <div class="flex items-center justify-between rounded-[14px] border border-black/10 bg-[rgba(236,236,240,0.8)] px-[16px] py-[10px]">
            <div class="flex items-center gap-[8px]">
              <div class="flex h-[12px] w-[12px] items-center justify-center rounded-full border border-[#00A63E]">
                <div class="h-[6px] w-[6px] rounded-full bg-[#00A63E]" />
              </div>
              <span class="text-[12px] leading-[16px] text-[#0A0A0A]">生成完成</span>
            </div>
            <div class="flex items-center gap-[8px] text-[12px] leading-[16px] text-[#717182]">
              <span>共生成 {{ generatedCount }} 条</span>
              <span>·</span>
              <span>已选 {{ selectedCount }} 条入库</span>
              <span>·</span>
              <span class="text-[#D08700]">去重 {{ dedupRemovedCount }} 条</span>
              <span>·</span>
              <span class="text-[#FF6900]">低置信度 {{ lowConfidenceCount }} 条</span>
            </div>
          </div>

          <div class="overflow-hidden rounded-[10px] border border-black/10">
            <div class="grid h-[52px] grid-cols-[37px_246px_96px_96px_160px_56px_48px_65px_56px] items-center bg-[rgba(236,236,240,0.8)]">
              <div class="pl-[12px]">
                <input type="checkbox" class="h-[13px] w-[13px]" :checked="allSelected" @change="toggleSelectAll(($event.target as HTMLInputElement).checked)" />
              </div>
              <div class="pl-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">标题</div>
              <div class="pl-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">Feature</div>
              <div class="pl-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">Story</div>
              <div class="pl-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">调用 URL</div>
              <div class="pl-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">类型</div>
              <div class="pl-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">优先级</div>
              <div class="pl-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">置信度</div>
              <div />
            </div>
            <div class="max-h-[287px] overflow-auto">
              <div v-for="item in previewCases" :key="item.id" class="grid h-[55px] grid-cols-[37px_246px_96px_96px_160px_56px_48px_65px_56px] items-center border-t border-black/10">
                <div class="pl-[12px]">
                  <input type="checkbox" class="h-[13px] w-[13px]" :checked="selectedCaseIds.includes(item.id)" @change="toggleCaseSelected(item.id, ($event.target as HTMLInputElement).checked)" />
                </div>
                <div class="flex flex-col gap-[2px] pl-[12px]">
                  <div class="truncate text-[12px] font-medium leading-[16px] text-[#0A0A0A]">{{ item.title }}</div>
                  <div class="truncate text-[12px] leading-[16px] text-[#717182]">{{ item.description }}</div>
                </div>
                <div class="truncate pl-[12px] text-[12px] leading-[16px] text-[#717182]">{{ item.feature }}</div>
                <div class="truncate pl-[12px] text-[12px] leading-[16px] text-[#717182]">{{ item.story }}</div>
                <div class="flex items-center gap-[6px] pl-[12px]">
                  <span class="rounded-[4px] bg-[#DBEAFE] px-[6px] py-[2px] text-[10px] font-bold leading-[13px] text-[#1447E6]">{{ item.method }}</span>
                  <span class="truncate font-['Consolas'] text-[11px] leading-[15px] text-[#717182]">{{ item.url }}</span>
                </div>
                <div class="pl-[12px]">
                  <span class="rounded-full bg-[#DBEAFE] px-[6px] py-[2px] text-[10px] font-medium leading-[13px] text-[#1447E6]">{{ item.caseType }}</span>
                </div>
                <div class="pl-[12px]">
                  <span class="rounded-full bg-[#FFEDD4] px-[6px] py-[2px] text-[10px] font-medium leading-[13px] text-[#CA3500]">{{ item.priority }}</span>
                </div>
                <div class="pl-[12px]">
                  <span class="text-[12px] font-medium leading-[16px]" :class="confidenceTextClass(item.confidence)">{{ item.confidence }}%</span>
                </div>
                <div class="pl-[16px]">
                  <button type="button" class="flex h-[22px] w-[22px] items-center justify-center rounded-[4px] text-[#FF6467]" @click="removePreviewCase(item.id)">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                      <path d="M4.6665 4.66675L9.33317 9.33341M9.33317 4.66675L4.6665 9.33341" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex h-[68.67px] items-center justify-between border-t border-black/10 px-[24px]">
        <button type="button" class="h-[36px] w-[61.33px] rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#0A0A0A]" @click="closeModal">
          取消
        </button>
        <button
          v-if="currentStep === 1"
          type="button"
          class="relative h-[36px] w-[140px] rounded-[10px] bg-[#155DFC]"
          :class="canStartGeneration ? 'opacity-100' : 'opacity-50'"
          :disabled="!canStartGeneration"
          @click="handleStart"
        >
          <img :src="modalCreateIcon" alt="" class="absolute left-[20px] top-[11px] h-[14px] w-[14px]" />
          <span class="absolute left-[42px] top-[8px] text-[14px] font-medium leading-[20px] text-white">开始生成</span>
          <img :src="filterChevron" alt="" class="absolute right-[16px] top-[11px] h-[14px] w-[14px] -rotate-90" />
        </button>
        <button
          v-else-if="currentStep === 2"
          type="button"
          class="h-[36px] w-[140px] rounded-[10px] bg-[#155DFC] text-[14px] font-medium leading-[20px] text-white opacity-70"
          disabled
        >
          生成中...
        </button>
        <div v-else class="flex items-center gap-[8px]">
          <button type="button" class="flex h-[36px] items-center gap-[8px] rounded-[10px] border border-black/10 px-[16px] text-[14px] font-medium leading-[20px] text-[#717182]" @click="regenerateCases">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M11.375 6.5C11.375 9.19139 9.19139 11.375 6.5 11.375C3.80861 11.375 1.625 9.19139 1.625 6.5C1.625 3.80861 3.80861 1.625 6.5 1.625C8.12312 1.625 9.56082 2.42017 10.4452 3.64261" stroke="currentColor" stroke-width="1.1" stroke-linecap="round" />
              <path d="M10.8335 1.89575V4.33325H8.396" stroke="currentColor" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            重新生成
          </button>
          <button
            type="button"
            class="flex h-[36px] items-center gap-[8px] rounded-[10px] border border-black/10 px-[16px] text-[14px] font-medium leading-[20px] text-[#0A0A0A]"
            :disabled="selectedCount === 0 || isDownloading"
            :class="selectedCount > 0 && !isDownloading ? 'opacity-100' : 'opacity-50'"
            @click="downloadCsv"
          >
            {{ isDownloading ? '下载中...' : '下载 CSV' }}
          </button>
          <button type="button" class="flex h-[36px] items-center gap-[8px] rounded-[10px] bg-[#155DFC] px-[20px] text-[14px] font-medium leading-[20px] text-white" :disabled="selectedCount === 0 || isImporting" :class="selectedCount > 0 && !isImporting ? 'opacity-100' : 'opacity-50'" @click="importCases">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M6.5 1.625V11.375M1.625 6.5H11.375" stroke="white" stroke-width="1.1" stroke-linecap="round" />
            </svg>
            {{ isImporting ? '入库中...' : `入库 ${selectedCount} 条` }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
