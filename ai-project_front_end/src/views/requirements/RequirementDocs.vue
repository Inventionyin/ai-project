<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  createRequirementDoc,
  deleteRequirementDoc,
  fetchRequirementDocs,
  updateRequirementDoc,
  type RequirementDoc,
  type RequirementDocStatus,
  type RequirementSourceType
} from '@/lib/api/requirements'
import { confirmAction } from '@/lib/ui/confirm'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.projectId || '').trim())

const loading = ref(false)
const creating = ref(false)
const error = ref('')
const success = ref('')

const q = ref('')
const statusFilter = ref('')
const docs = ref<RequirementDoc[]>([])
const editingDocId = ref('')
const editingDocForm = ref({
  title: '',
  status: 'DRAFT' as RequirementDocStatus,
  sourceType: 'PRD' as RequirementSourceType,
  tags: ''
})

const createOpen = ref(false)
const createForm = ref({
  title: '',
  status: 'DRAFT' as RequirementDocStatus,
  tags: '',
  sourceType: 'PRD' as RequirementSourceType
})

const statusOptions: Array<{ label: string; value: RequirementDocStatus }> = [
  { label: '草稿', value: 'DRAFT' },
  { label: '评审中', value: 'REVIEWING' },
  { label: '已发布', value: 'PUBLISHED' },
  { label: '已归档', value: 'ARCHIVED' }
]

function sourceTypeText(value: RequirementSourceType) {
  if (value === 'PRD') return 'PRD'
  if (value === 'SPEC') return 'SPEC'
  if (value === 'PROTOTYPE') return 'Prototype'
  return 'Other'
}

function statusText(value: RequirementDocStatus) {
  return statusOptions.find((item) => item.value === value)?.label || value
}

function statusClass(value: RequirementDocStatus) {
  if (value === 'PUBLISHED') return 'bg-[#DCFCE7] text-[#166534]'
  if (value === 'REVIEWING') return 'bg-[#FEF3C7] text-[#92400E]'
  if (value === 'ARCHIVED') return 'bg-[#E5E7EB] text-[#4B5563]'
  return 'bg-[#DBEAFE] text-[#1D4ED8]'
}

async function loadDocs() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await fetchRequirementDocs(projectId.value, {
      page: 1,
      pageSize: 50,
      status: statusFilter.value || undefined,
      q: q.value.trim() || undefined
    })
    docs.value = data.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载文档失败'
    docs.value = []
  } finally {
    loading.value = false
  }
}

function resetCreateForm() {
  createForm.value = {
    title: '',
    status: 'DRAFT',
    tags: '',
    sourceType: 'PRD'
  }
}

async function submitCreate() {
  if (!projectId.value) return
  creating.value = true
  error.value = ''
  success.value = ''
  try {
    const title = createForm.value.title.trim()
    if (!title) throw new Error('文档标题不能为空')
    const tags = createForm.value.tags
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
    const created = await createRequirementDoc(projectId.value, {
      title,
      status: createForm.value.status,
      tags,
      sourceType: createForm.value.sourceType
    })
    success.value = `创建成功：${created.title}`
    createOpen.value = false
    resetCreateForm()
    await loadDocs()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    creating.value = false
  }
}

function openDetail(doc: RequirementDoc) {
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/requirements/docs/${encodeURIComponent(doc.id)}`)
}

function openInlineEdit(doc: RequirementDoc) {
  editingDocId.value = doc.id
  editingDocForm.value = {
    title: doc.title,
    status: doc.status,
    sourceType: doc.sourceType,
    tags: doc.tags?.join(', ') || ''
  }
}

function closeInlineEdit() {
  editingDocId.value = ''
}

async function saveInlineEdit(doc: RequirementDoc) {
  if (!projectId.value) return
  const title = editingDocForm.value.title.trim()
  if (!title) {
    error.value = '文档标题不能为空'
    return
  }
  error.value = ''
  success.value = ''
  try {
    const tags = editingDocForm.value.tags
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
    const updated = await updateRequirementDoc(projectId.value, doc.id, {
      title,
      status: editingDocForm.value.status,
      sourceType: editingDocForm.value.sourceType,
      tags
    })
    docs.value = docs.value.map((item) => item.id === doc.id ? updated : item)
    success.value = `更新成功：${updated.title}`
    closeInlineEdit()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '更新失败'
  }
}

async function removeDoc(doc: RequirementDoc) {
  if (!projectId.value) return
  if (!await confirmAction(`确定删除需求文档？\n\n${doc.title}`)) return
  error.value = ''
  success.value = ''
  try {
    await deleteRequirementDoc(projectId.value, doc.id)
    docs.value = docs.value.filter((item) => item.id !== doc.id)
    success.value = `删除成功：${doc.title}`
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

watch(
  () => projectId.value,
  () => {
    void loadDocs()
  },
  { immediate: true }
)
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="rounded-[12px] border border-black/10 bg-white">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-black/10 px-4 py-3">
        <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">需求文档中心</div>
        <button class="h-8 rounded-[8px] bg-[#155DFC] px-3 text-[12px] text-white" @click="createOpen = !createOpen">
          {{ createOpen ? '收起创建' : '新建文档' }}
        </button>
      </div>

      <div class="grid grid-cols-1 gap-3 border-b border-black/10 p-4 md:grid-cols-[minmax(0,1fr)_180px_auto]">
        <input
          v-model="q"
          class="h-9 w-full rounded-[8px] border border-black/10 px-3 text-[13px] outline-none"
          placeholder="搜索标题/标签"
          @keyup.enter="loadDocs"
        />
        <select v-model="statusFilter" class="h-9 rounded-[8px] border border-black/10 px-2 text-[13px] outline-none">
          <option value="">全部状态</option>
          <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <button class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" @click="loadDocs">查询</button>
      </div>

      <div v-if="createOpen" class="border-b border-black/10 bg-[#FAFAFA] p-4">
        <div class="grid grid-cols-1 gap-3 md:grid-cols-4">
          <input v-model="createForm.title" class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="文档标题" />
          <select v-model="createForm.status" class="h-9 rounded-[8px] border border-black/10 px-2 text-[13px]">
            <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
          <select v-model="createForm.sourceType" class="h-9 rounded-[8px] border border-black/10 px-2 text-[13px]">
            <option value="PRD">PRD</option>
            <option value="SPEC">SPEC</option>
            <option value="PROTOTYPE">Prototype</option>
            <option value="OTHER">Other</option>
          </select>
          <input v-model="createForm.tags" class="h-9 rounded-[8px] border border-black/10 px-3 text-[13px]" placeholder="标签，逗号分隔" />
        </div>
        <div class="mt-3">
          <button class="h-9 rounded-[8px] bg-[#155DFC] px-4 text-[13px] text-white disabled:opacity-60" :disabled="creating" @click="submitCreate">
            {{ creating ? '创建中...' : '确认创建' }}
          </button>
        </div>
      </div>

      <div v-if="loading" class="px-4 py-5 text-[13px] text-[#717182]">加载中...</div>
      <div v-else-if="error" class="px-4 py-5 text-[13px] text-[#B91C1C]">{{ error }}</div>
      <div v-else-if="docs.length === 0" class="px-4 py-8 text-center text-[13px] text-[#717182]">暂无文档，先创建第一份需求文档。</div>
      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[860px] border-collapse">
          <thead>
            <tr class="bg-[rgba(236,236,240,0.3)]">
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">标题</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">状态</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">来源</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">标签</th>
              <th class="px-4 py-2 text-left text-[12px] font-medium text-[#717182]">更新时间</th>
              <th class="px-4 py-2 text-right text-[12px] font-medium text-[#717182]">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in docs" :key="doc.id" class="cursor-pointer border-t border-black/10 hover:bg-[#F8FAFC]" @click="openDetail(doc)">
              <td class="px-4 py-3 text-[13px] text-[#0A0A0A]">
                <input
                  v-if="editingDocId === doc.id"
                  v-model="editingDocForm.title"
                  aria-label="编辑标题"
                  class="h-8 w-full rounded-[8px] border border-black/10 px-2 text-[13px] outline-none focus:border-[#155DFC]"
                  @click.stop
                />
                <span v-else>{{ doc.title }}</span>
              </td>
              <td class="px-4 py-3">
                <select
                  v-if="editingDocId === doc.id"
                  v-model="editingDocForm.status"
                  class="h-8 rounded-[8px] border border-black/10 px-2 text-[12px] outline-none focus:border-[#155DFC]"
                  @click.stop
                >
                  <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                </select>
                <span v-else class="rounded-full px-2 py-[2px] text-[11px] font-medium" :class="statusClass(doc.status)">{{ statusText(doc.status) }}</span>
              </td>
              <td class="px-4 py-3 text-[12px] text-[#4A5565]">
                <select
                  v-if="editingDocId === doc.id"
                  v-model="editingDocForm.sourceType"
                  class="h-8 rounded-[8px] border border-black/10 px-2 text-[12px] outline-none focus:border-[#155DFC]"
                  @click.stop
                >
                  <option value="PRD">PRD</option>
                  <option value="SPEC">SPEC</option>
                  <option value="PROTOTYPE">Prototype</option>
                  <option value="OTHER">Other</option>
                </select>
                <span v-else>{{ sourceTypeText(doc.sourceType) }}</span>
              </td>
              <td class="px-4 py-3 text-[12px] text-[#4A5565]">
                <input
                  v-if="editingDocId === doc.id"
                  v-model="editingDocForm.tags"
                  class="h-8 w-full rounded-[8px] border border-black/10 px-2 text-[12px] outline-none focus:border-[#155DFC]"
                  @click.stop
                />
                <span v-else>{{ doc.tags?.join(', ') || '-' }}</span>
              </td>
              <td class="px-4 py-3 text-[12px] text-[#717182]">{{ doc.updatedAt || '-' }}</td>
              <td class="px-4 py-3">
                <div class="flex justify-end gap-2">
                  <template v-if="editingDocId === doc.id">
                    <button class="h-8 rounded-[8px] bg-[#155DFC] px-3 text-[12px] text-white" :aria-label="`保存 ${doc.title}`" @click.stop="saveInlineEdit(doc)">保存</button>
                    <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px] text-[#717182]" @click.stop="closeInlineEdit">取消</button>
                  </template>
                  <template v-else>
                    <button class="h-8 rounded-[8px] border border-black/10 px-3 text-[12px] text-[#155DFC]" :aria-label="`编辑 ${doc.title}`" @click.stop="openInlineEdit(doc)">编辑</button>
                    <button class="h-8 rounded-[8px] border border-red-200 px-3 text-[12px] text-red-700" :aria-label="`删除 ${doc.title}`" @click.stop="removeDoc(doc)">删除</button>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="success" class="border-t border-black/10 px-4 py-2 text-[12px] text-[#166534]">{{ success }}</div>
    </div>
  </div>
</template>
