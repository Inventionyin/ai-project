<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">测试执行器</div>
          <div class="text-[12px] text-[#717182] mt-1">管理测试执行器，支持多种测试框架接入</div>
        </div>
        <button @click="showCreate = true" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded hover:bg-blue-700">新建执行器</button>
      </div>

      <div v-if="showCreate" class="mb-4 p-4 border border-black/10 rounded bg-gray-50">
        <div class="text-[13px] font-medium mb-2">新建执行器</div>
        <div class="grid grid-cols-2 gap-3">
          <input v-model="form.name" placeholder="执行器名称" class="text-[12px] border rounded px-2 py-1" />
          <select v-model="form.executorType" class="text-[12px] border rounded px-2 py-1">
            <option value="PYTEST">Pytest</option>
            <option value="K6">K6</option>
            <option value="PLAYWRIGHT">Playwright</option>
            <option value="JMETER">JMeter</option>
            <option value="POSTMAN">Postman</option>
          </select>
          <input v-model="form.description" placeholder="描述（可选）" class="text-[12px] border rounded px-2 py-1" />
          <input v-model="form.version" placeholder="版本（可选）" class="text-[12px] border rounded px-2 py-1" />
        </div>
        <div class="flex gap-2 mt-3">
          <button @click="create" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded">创建</button>
          <button @click="showCreate = false" class="text-[12px] px-3 py-1 border rounded">取消</button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-8 text-[12px] text-[#717182]">加载中...</div>
      <div v-else-if="executors.length === 0" class="text-center py-8 text-[12px] text-[#717182]">暂无执行器，点击"新建执行器"创建</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="e in executors" :key="e.id" class="border border-black/10 rounded p-4">
          <div class="flex items-center justify-between mb-2">
            <div class="text-[14px] font-medium">{{ e.name }}</div>
            <span :class="e.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'" class="px-2 py-0.5 rounded text-[11px]">
              {{ e.enabled ? '已启用' : '已禁用' }}
            </span>
          </div>
          <div class="text-[11px] text-[#717182] space-y-1">
            <div>类型: <span class="font-medium text-[#0A0A0A]">{{ e.executorType }}</span></div>
            <div v-if="e.version">版本: {{ e.version }}</div>
            <div v-if="e.description">{{ e.description }}</div>
          </div>
          <div class="flex gap-2 mt-3">
            <button @click="toggle(e)" class="text-[11px] px-2 py-0.5 border rounded hover:bg-gray-50">
              {{ e.enabled ? '禁用' : '启用' }}
            </button>
            <button @click="remove(e.id)" class="text-[11px] px-2 py-0.5 bg-red-500 text-white rounded hover:bg-red-600">删除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { listExecutors, createExecutor, updateExecutor, deleteExecutor, type Executor } from '@/lib/api/executors'

const route = useRoute()
const projectId = route.params.projectId as string

const executors = ref<Executor[]>([])
const loading = ref(false)
const showCreate = ref(false)
const form = ref({ name: '', executorType: 'PYTEST', description: '', version: '' })

async function load() {
  loading.value = true
  try {
    const res = await listExecutors(projectId)
    executors.value = res.items
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.value.name) return
  await createExecutor(projectId, form.value)
  showCreate.value = false
  form.value = { name: '', executorType: 'PYTEST', description: '', version: '' }
  await load()
}

async function toggle(e: Executor) {
  await updateExecutor(projectId, e.id, { enabled: !e.enabled })
  await load()
}

async function remove(id: string) {
  await deleteExecutor(projectId, id)
  await load()
}

onMounted(load)
</script>
