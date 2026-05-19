<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchKnowledgeTemplates, createKnowledgeTemplate } from '@/lib/api/knowledge'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || route.params.id || '').trim())

const templates = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const showCreate = ref(false)
const newName = ref('')
const newContent = ref('')
const creating = ref(false)

async function load() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    templates.value = await fetchKnowledgeTemplates(projectId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载模板失败'
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!newName.value.trim() || !projectId.value) return
  creating.value = true
  try {
    await createKnowledgeTemplate(projectId.value, { name: newName.value.trim(), content: newContent.value })
    showCreate.value = false
    newName.value = ''
    newContent.value = ''
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建模板失败'
  } finally {
    creating.value = false
  }
}

onMounted(load)
watch(projectId, load)
</script>

<template>
  <div class="p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-[20px] font-semibold text-[#0A0A0A]">知识模板</h1>
        <p class="mt-1 text-[14px] text-[#717182]">管理复盘和分析的模板（共 {{ templates.length }} 个）</p>
      </div>
      <button class="rounded-[8px] bg-[#155DFC] px-4 py-2 text-[14px] font-medium text-white" @click="showCreate = true">
        新建模板
      </button>
    </div>

    <div v-if="error" class="mb-4 rounded bg-red-50 p-3 text-[13px] text-red-600">{{ error }}</div>
    <div v-if="loading" class="py-8 text-center text-[14px] text-[#717182]">加载中...</div>

    <div v-else-if="templates.length === 0" class="py-12 text-center text-[14px] text-[#717182]">暂无模板</div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="t in templates" :key="t.id" class="rounded-[10px] border border-black/10 p-4 hover:shadow-sm">
        <h3 class="text-[14px] font-medium text-[#0A0A0A]">{{ t.name }}</h3>
        <p v-if="t.category" class="mt-1 text-[12px] text-[#717182]">{{ t.category }}</p>
        <p class="mt-2 line-clamp-3 text-[13px] text-[#4A5565]">{{ t.content || '无内容' }}</p>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div class="w-[480px] rounded-[12px] bg-white p-6 shadow-lg">
        <h2 class="mb-4 text-[16px] font-semibold">新建知识模板</h2>
        <div class="mb-3">
          <label class="mb-1 block text-[12px] font-medium text-[#717182]">名称</label>
          <input v-model="newName" type="text" class="w-full rounded border border-black/10 px-3 py-2 text-[13px] outline-none focus:border-[#155DFC]" placeholder="模板名称" />
        </div>
        <div class="mb-4">
          <label class="mb-1 block text-[12px] font-medium text-[#717182]">内容</label>
          <textarea v-model="newContent" rows="6" class="w-full rounded border border-black/10 px-3 py-2 text-[13px] outline-none focus:border-[#155DFC]" placeholder="模板内容..." />
        </div>
        <div class="flex justify-end gap-2">
          <button class="rounded border border-black/10 px-4 py-2 text-[13px] text-[#717182]" @click="showCreate = false">取消</button>
          <button class="rounded bg-[#155DFC] px-4 py-2 text-[13px] text-white disabled:opacity-50" :disabled="!newName.trim() || creating" @click="handleCreate">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
