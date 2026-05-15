<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  deleteRequirementDoc,
  fetchRequirementDoc,
  fetchRequirementAnalyses,
  fetchRequirementDocParsedText,
  fetchRequirementDocVersions,
  generateRequirementAnalysis,
  parseRequirementDocVersion,
  updateRequirementDoc,
  uploadRequirementDocVersion,
  type RequirementDoc,
  type RequirementAnalysis,
  type RequirementDocStatus,
  type RequirementDocVersion,
  type RequirementSourceType
} from '@/lib/api/requirements'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.projectId || '').trim())
const docId = computed(() => String(route.params.docId || '').trim())

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const uploading = ref(false)
const parsingVersionId = ref('')
const loadingParsed = ref(false)

const error = ref('')
const success = ref('')

const detail = ref<RequirementDoc | null>(null)
const versions = ref<RequirementDocVersion[]>([])
const selectedVersionId = ref('')
const parsedText = ref('')
const analyses = ref<RequirementAnalysis[]>([])
const analyzingVersionId = ref('')
const analysisInstruction = ref('')

const form = ref({
  title: '',
  status: 'DRAFT' as RequirementDocStatus,
  tagsText: '',
  sourceType: 'PRD' as RequirementSourceType
})

const uploadForm = ref({
  file: null as File | null,
  changeSummary: '',
  effectiveScope: ''
})

const statusOptions: Array<{ label: string; value: RequirementDocStatus }> = [
  { label: '草稿', value: 'DRAFT' },
  { label: '评审中', value: 'REVIEWING' },
  { label: '已发布', value: 'PUBLISHED' },
  { label: '已归档', value: 'ARCHIVED' }
]

function fillForm(doc: RequirementDoc) {
  form.value = {
    title: doc.title || '',
    status: doc.status || 'DRAFT',
    tagsText: (doc.tags || []).join(', '),
    sourceType: doc.sourceType || 'PRD'
  }
}

async function loadDetail() {
  if (!projectId.value || !docId.value) return
  loading.value = true
  error.value = ''
  try {
    const [doc, list, analysisList] = await Promise.all([
      fetchRequirementDoc(projectId.value, docId.value),
      fetchRequirementDocVersions(projectId.value, docId.value),
      fetchRequirementAnalyses(projectId.value, { docId: docId.value })
    ])
    detail.value = doc
    versions.value = list
    analyses.value = analysisList
    fillForm(doc)
    selectedVersionId.value = list[0]?.id || ''
    parsedText.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载详情失败'
    detail.value = null
    versions.value = []
    analyses.value = []
  } finally {
    loading.value = false
  }
}

async function saveMeta() {
  if (!projectId.value || !docId.value) return
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const title = form.value.title.trim()
    if (!title) throw new Error('标题不能为空')
    const tags = form.value.tagsText
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
    const updated = await updateRequirementDoc(projectId.value, docId.value, {
      title,
      status: form.value.status,
      tags,
      sourceType: form.value.sourceType
    })
    detail.value = updated
    fillForm(updated)
    success.value = '文档信息已保存'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function removeDoc() {
  if (!projectId.value || !docId.value) return
  if (!window.confirm('确认删除该文档吗？')) return
  deleting.value = true
  error.value = ''
  try {
    await deleteRequirementDoc(projectId.value, docId.value)
    void router.push(`/projects/${encodeURIComponent(projectId.value)}/requirements/docs`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  } finally {
    deleting.value = false
  }
}

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null
  uploadForm.value.file = target?.files?.[0] || null
}

async function submitUploadVersion() {
  if (!projectId.value || !docId.value) return
  if (!uploadForm.value.file) {
    error.value = '请先选择文件'
    return
  }
  uploading.value = true
  error.value = ''
  success.value = ''
  try {
    await uploadRequirementDocVersion(projectId.value, docId.value, {
      file: uploadForm.value.file,
      changeSummary: uploadForm.value.changeSummary.trim(),
      effectiveScope: uploadForm.value.effectiveScope.trim()
    })
    uploadForm.value = { file: null, changeSummary: '', effectiveScope: '' }
    await loadDetail()
    success.value = '新版本上传成功'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上传失败'
  } finally {
    uploading.value = false
  }
}

async function triggerParse(versionId: string) {
  if (!projectId.value || !docId.value || !versionId) return
  parsingVersionId.value = versionId
  error.value = ''
  try {
    await parseRequirementDocVersion(projectId.value, docId.value, versionId)
    await loadDetail()
    success.value = '已触发解析'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '触发解析失败'
  } finally {
    parsingVersionId.value = ''
  }
}

async function loadParsedText() {
  if (!projectId.value || !docId.value || !selectedVersionId.value) return
  loadingParsed.value = true
  parsedText.value = ''
  error.value = ''
  try {
    parsedText.value = await fetchRequirementDocParsedText(projectId.value, docId.value, selectedVersionId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载解析文本失败'
  } finally {
    loadingParsed.value = false
  }
}

function analysisForVersion(versionId: string) {
  return analyses.value.find((item) => item.docVersionId === versionId)
}

async function createAnalysis(versionId: string) {
  if (!projectId.value || !docId.value || !versionId) return
  analyzingVersionId.value = versionId
  error.value = ''
  success.value = ''
  try {
    const created = await generateRequirementAnalysis(projectId.value, docId.value, versionId, analysisInstruction.value.trim())
    await loadDetail()
    success.value = '需求分析已生成'
    void router.push(`/projects/${encodeURIComponent(projectId.value)}/requirements/analyses/${encodeURIComponent(created.id)}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成需求分析失败'
  } finally {
    analyzingVersionId.value = ''
  }
}

function openAnalysis(analysisId: string) {
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/requirements/analyses/${encodeURIComponent(analysisId)}`)
}

watch(
  () => [projectId.value, docId.value],
  () => {
    void loadDetail()
  },
  { immediate: true }
)
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div v-if="loading" class="rounded-[12px] border border-black/10 bg-white px-4 py-5 text-[13px] text-[#717182]">加载中...</div>
    <div v-else-if="error && !detail" class="rounded-[12px] border border-black/10 bg-white px-4 py-5 text-[13px] text-[#B91C1C]">{{ error }}</div>
    <div v-else-if="detail" class="grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <section class="rounded-[12px] border border-black/10 bg-white p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-[14px] font-semibold text-[#0A0A0A]">文档元数据</h2>
          <button class="h-8 rounded-[8px] border border-[#EF4444]/30 px-3 text-[12px] text-[#B91C1C] disabled:opacity-60" :disabled="deleting" @click="removeDoc">
            删除文档
          </button>
        </div>

        <div class="space-y-3">
          <label class="block text-[12px] text-[#717182]">
            标题
            <input v-model="form.title" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A]" />
          </label>
          <label class="block text-[12px] text-[#717182]">
            状态
            <select v-model="form.status" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-2 text-[13px] text-[#0A0A0A]">
              <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <label class="block text-[12px] text-[#717182]">
            来源类型
            <select v-model="form.sourceType" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-2 text-[13px] text-[#0A0A0A]">
              <option value="PRD">PRD</option>
              <option value="SPEC">SPEC</option>
              <option value="PROTOTYPE">Prototype</option>
              <option value="OTHER">Other</option>
            </select>
          </label>
          <label class="block text-[12px] text-[#717182]">
            标签（逗号分隔）
            <input v-model="form.tagsText" class="mt-1 h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] text-[#0A0A0A]" />
          </label>
        </div>

        <button class="mt-4 h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] text-white disabled:opacity-60" :disabled="saving" @click="saveMeta">
          {{ saving ? '保存中...' : '保存元数据' }}
        </button>

        <div class="mt-6 border-t border-black/10 pt-4">
          <h3 class="text-[13px] font-medium text-[#0A0A0A]">上传新版本</h3>
          <div class="mt-3 space-y-3">
            <input type="file" class="block w-full text-[12px]" @change="handleFileChange" />
            <input v-model="uploadForm.changeSummary" class="h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="变更摘要" />
            <input v-model="uploadForm.effectiveScope" class="h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="影响范围" />
            <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px] disabled:opacity-60" :disabled="uploading" @click="submitUploadVersion">
              {{ uploading ? '上传中...' : '上传版本' }}
            </button>
          </div>
        </div>
      </section>

      <section class="rounded-[12px] border border-black/10 bg-white">
        <div class="border-b border-black/10 px-4 py-3 text-[14px] font-semibold text-[#0A0A0A]">版本列表与解析</div>
        <div class="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[380px_minmax(0,1fr)]">
          <div class="space-y-2">
            <div class="rounded-[8px] border border-black/10 bg-[#FAFAFA] p-3">
              <div class="text-[12px] font-medium text-[#0A0A0A]">分析指令</div>
              <textarea
                v-model="analysisInstruction"
                class="mt-2 min-h-[72px] w-full resize-y rounded-[8px] border border-black/10 px-3 py-2 text-[12px]"
                placeholder="例如：重点覆盖权限、异常流程、边界值和回归风险"
              />
            </div>
            <div v-if="versions.length === 0" class="rounded-[8px] border border-dashed border-black/10 p-4 text-[12px] text-[#717182]">暂无版本记录</div>
            <button
              v-for="version in versions"
              :key="version.id"
              class="block w-full rounded-[8px] border px-3 py-2 text-left"
              :class="selectedVersionId === version.id ? 'border-[#155DFC] bg-[#EFF6FF]' : 'border-black/10 bg-white'"
              @click="selectedVersionId = version.id"
            >
              <div class="text-[13px] font-medium text-[#0A0A0A]">{{ version.version || version.id }}</div>
              <div class="mt-1 text-[12px] text-[#717182]">状态：{{ version.parseStatus || '-' }}</div>
              <div class="mt-2 flex gap-2">
                <button
                  class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] text-[#155DFC] disabled:opacity-60"
                  :disabled="parsingVersionId === version.id"
                  @click.stop="triggerParse(version.id)"
                >
                  {{ parsingVersionId === version.id ? '处理中...' : '触发解析' }}
                </button>
                <button
                  v-if="analysisForVersion(version.id)"
                  class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] text-[#155DFC]"
                  @click.stop="openAnalysis(analysisForVersion(version.id)!.id)"
                >
                  查看分析
                </button>
                <button
                  v-else
                  class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] text-[#155DFC] disabled:opacity-60"
                  :disabled="analyzingVersionId === version.id"
                  @click.stop="createAnalysis(version.id)"
                >
                  {{ analyzingVersionId === version.id ? '生成中...' : '生成分析' }}
                </button>
              </div>
            </button>
          </div>

          <div class="rounded-[10px] border border-black/10 bg-[#FAFAFA] p-3">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div class="text-[13px] font-medium text-[#0A0A0A]">解析文本预览</div>
              <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px] disabled:opacity-60" :disabled="!selectedVersionId || loadingParsed" @click="loadParsedText">
                {{ loadingParsed ? '加载中...' : '加载文本' }}
              </button>
            </div>
            <pre class="max-h-[540px] min-h-[360px] overflow-auto whitespace-pre-wrap break-all rounded-[8px] border border-black/10 bg-white p-3 text-[12px] text-[#0A0A0A]">{{ parsedText || '请选择版本后加载解析文本。' }}</pre>
          </div>
        </div>

        <div v-if="error" class="border-t border-black/10 px-4 py-2 text-[12px] text-[#B91C1C]">{{ error }}</div>
        <div v-else-if="success" class="border-t border-black/10 px-4 py-2 text-[12px] text-[#166534]">{{ success }}</div>
      </section>
    </div>
  </div>
</template>
