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
import {
  createRequirementChangeSet,
  fetchRequirementChangeSets,
  type RequirementChangeSetDetail
} from '@/lib/api/requirementChanges'

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
const changeSets = ref<RequirementChangeSetDetail[]>([])
const selectedBaselineVersionId = ref('')
const creatingChangeSet = ref(false)
const changeSetsLoading = ref(false)
const changeSetsError = ref('')
let docLoadSeq = 0
let changeSetLoadSeq = 0

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
  const pid = projectId.value
  const did = docId.value
  if (!pid || !did) return
  const seq = ++docLoadSeq
  loading.value = true
  error.value = ''
  changeSetsError.value = ''
  changeSets.value = []
  try {
    const [doc, list, analysisList] = await Promise.all([
      fetchRequirementDoc(pid, did),
      fetchRequirementDocVersions(pid, did),
      fetchRequirementAnalyses(pid, { docId: did })
    ])
    if (seq !== docLoadSeq || pid !== projectId.value || did !== docId.value) return
    detail.value = doc
    versions.value = list
    analyses.value = analysisList
    fillForm(doc)
    selectedVersionId.value = list[0]?.id || ''
    selectedBaselineVersionId.value = list[1]?.id || list[0]?.id || ''
    parsedText.value = ''
    void loadChangeSets(pid, did)
  } catch (e) {
    if (seq !== docLoadSeq) return
    error.value = e instanceof Error ? e.message : '加载详情失败'
    detail.value = null
    versions.value = []
    analyses.value = []
    changeSets.value = []
  } finally {
    if (seq === docLoadSeq) loading.value = false
  }
}

async function loadChangeSets(pid = projectId.value, did = docId.value) {
  if (!pid || !did) return
  const seq = ++changeSetLoadSeq
  changeSetsLoading.value = true
  changeSetsError.value = ''
  try {
    const rows = await fetchRequirementChangeSets(pid, did)
    if (seq !== changeSetLoadSeq || pid !== projectId.value || did !== docId.value) return
    changeSets.value = rows
  } catch (e) {
    if (seq !== changeSetLoadSeq) return
    changeSetsError.value = e instanceof Error ? e.message : '加载变更分析记录失败'
  } finally {
    if (seq === changeSetLoadSeq) changeSetsLoading.value = false
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

async function createChangeSet() {
  const pid = projectId.value
  const did = docId.value
  if (!pid || !did) return
  if (!selectedBaselineVersionId.value || !selectedVersionId.value) {
    error.value = '请选择基线版本和目标版本'
    return
  }
  creatingChangeSet.value = true
  error.value = ''
  success.value = ''
  try {
    const created = await createRequirementChangeSet(pid, did, {
      baselineVersionId: selectedBaselineVersionId.value,
      targetVersionId: selectedVersionId.value
    })
    changeSets.value = [created, ...changeSets.value.filter((item) => item.id !== created.id)]
    success.value = '变更影响分析已生成'
    void router.push(`/projects/${encodeURIComponent(pid)}/requirements/change-sets/${encodeURIComponent(created.id)}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成变更影响分析失败'
  } finally {
    creatingChangeSet.value = false
  }
}

function openChangeSet(changeSetId: string) {
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/requirements/change-sets/${encodeURIComponent(changeSetId)}`)
}

function versionLabel(versionId: string) {
  const version = versions.value.find((item) => item.id === versionId)
  if (!version) return versionId
  const label = String(version.version ?? '').trim()
  return `v${label || version.id}`
}

function formatTime(ts?: number | null) {
  if (!ts) return '-'
  const value = ts < 100000000000 ? ts * 1000 : ts
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(
    date.getHours()
  ).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
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
            <div class="rounded-[8px] border border-black/10 bg-[#FAFAFA] p-3">
              <div class="flex items-center justify-between gap-2">
                <div>
                  <div class="text-[12px] font-medium text-[#0A0A0A]">变更影响分析</div>
                  <div class="mt-1 text-[11px] text-[#717182]">选择基线版本和目标版本，生成影响项与回归集入口。</div>
                </div>
                <button
                  class="h-8 shrink-0 rounded-[8px] bg-[#155DFC] px-3 text-[12px] text-white disabled:opacity-60"
                  :disabled="versions.length < 2 || !selectedBaselineVersionId || !selectedVersionId || selectedBaselineVersionId === selectedVersionId || creatingChangeSet"
                  @click="createChangeSet"
                >
                  {{ creatingChangeSet ? '生成中...' : '生成' }}
                </button>
              </div>
              <div class="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <label class="block text-[11px] text-[#717182]">
                  基线版本
                  <select v-model="selectedBaselineVersionId" class="mt-1 h-8 w-full rounded-[8px] border border-black/10 bg-white px-2 text-[12px] text-[#0A0A0A]">
                    <option value="">请选择</option>
                    <option v-for="version in versions" :key="`base-${version.id}`" :value="version.id">
                      v{{ version.version || version.id }}
                    </option>
                  </select>
                </label>
                <label class="block text-[11px] text-[#717182]">
                  目标版本
                  <select v-model="selectedVersionId" class="mt-1 h-8 w-full rounded-[8px] border border-black/10 bg-white px-2 text-[12px] text-[#0A0A0A]">
                    <option value="">请选择</option>
                    <option v-for="version in versions" :key="`target-${version.id}`" :value="version.id">
                      v{{ version.version || version.id }}
                    </option>
                  </select>
                </label>
              </div>
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

            <div class="rounded-[8px] border border-black/10 bg-white">
              <div class="flex items-center justify-between gap-2 border-b border-black/10 px-3 py-2">
                <div class="text-[12px] font-medium text-[#0A0A0A]">变更分析记录</div>
                <button class="h-7 rounded-[6px] border border-black/10 px-2 text-[11px] disabled:opacity-60" :disabled="changeSetsLoading" @click="loadChangeSets()">
                  {{ changeSetsLoading ? '刷新中...' : '刷新' }}
                </button>
              </div>
              <div v-if="changeSetsLoading && changeSets.length === 0" class="px-3 py-4 text-[12px] text-[#717182]">变更分析记录加载中...</div>
              <div v-else-if="changeSetsError" class="px-3 py-4 text-[12px] text-[#B91C1C]">{{ changeSetsError }}</div>
              <div v-else-if="changeSets.length === 0" class="px-3 py-4 text-[12px] text-[#717182]">暂无变更影响分析。</div>
              <button
                v-for="row in changeSets"
                :key="row.id"
                class="block w-full border-t border-black/10 px-3 py-2 text-left first:border-t-0 hover:bg-[#F8FAFC]"
                @click="openChangeSet(row.id)"
              >
                <div class="flex items-center justify-between gap-2">
                  <div class="min-w-0 text-[12px] font-medium text-[#0A0A0A]">{{ row.summary || '变更影响分析' }}</div>
                  <div class="shrink-0 rounded-[6px] bg-[#F4F4F5] px-2 py-1 text-[11px] text-[#4A5565]">{{ row.status }}</div>
                </div>
                <div class="mt-1 text-[11px] text-[#717182]">
                  {{ versionLabel(row.baselineVersionId) }} -> {{ versionLabel(row.targetVersionId) }} · {{ formatTime(row.createdAt) }}
                </div>
              </button>
            </div>
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
