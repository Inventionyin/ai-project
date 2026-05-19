<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">UI 自动化录制回放</div>
          <div class="text-[12px] text-[#717182] mt-1">录制 UI 操作，生成 Playwright 测试脚本并执行</div>
        </div>
        <div class="flex gap-2">
          <button @click="showCreate = true" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded hover:bg-blue-700">新建脚本</button>
        </div>
      </div>

      <!-- Create form -->
      <div v-if="showCreate" class="mb-4 p-4 border border-black/10 rounded bg-gray-50">
        <div class="text-[13px] font-medium mb-2">新建 UI 测试脚本</div>
        <div class="grid grid-cols-2 gap-3">
          <input v-model="createForm.name" placeholder="脚本名称" class="text-[12px] border rounded px-2 py-1" />
          <select v-model="createForm.browser" class="text-[12px] border rounded px-2 py-1">
            <option value="chromium">Chromium</option>
            <option value="firefox">Firefox</option>
            <option value="webkit">WebKit</option>
          </select>
          <input v-model="createForm.baseUrl" placeholder="基础 URL (https://example.com)" class="text-[12px] border rounded px-2 py-1 col-span-2" />
          <input v-model.number="createForm.viewportWidth" type="number" placeholder="视口宽度" class="text-[12px] border rounded px-2 py-1" />
          <input v-model.number="createForm.viewportHeight" type="number" placeholder="视口高度" class="text-[12px] border rounded px-2 py-1" />
          <textarea v-model="createForm.description" placeholder="描述" class="text-[12px] border rounded px-2 py-1 col-span-2" rows="2"></textarea>
        </div>
        <div class="flex gap-2 mt-3">
          <button @click="handleCreate" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded">创建</button>
          <button @click="showCreate = false" class="text-[12px] px-3 py-1 border rounded">取消</button>
        </div>
      </div>

      <!-- Script List -->
      <div v-if="loading" class="text-center py-8 text-[12px] text-[#717182]">加载中...</div>
      <div v-else-if="scripts.length === 0 && !showCreate" class="text-center py-8 text-[12px] text-[#717182]">
        暂无 UI 测试脚本，点击"新建脚本"开始
      </div>
      <div v-else class="space-y-3">
        <div v-for="s in scripts" :key="s.id" class="border border-black/10 rounded p-4">
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="text-[14px] font-medium">{{ s.name }}</span>
                <span :class="statusClass(s.status)" class="px-2 py-0.5 rounded text-[11px]">{{ s.status }}</span>
                <span class="text-[11px] text-[#717182]">{{ s.browser }} {{ s.viewportWidth }}x{{ s.viewportHeight }}</span>
              </div>
              <div v-if="s.description" class="text-[12px] text-[#717182] mt-1">{{ s.description }}</div>
              <div v-if="s.baseUrl" class="text-[11px] text-[#717182] mt-1 font-mono">{{ s.baseUrl }}</div>
            </div>
            <div class="flex items-center gap-2">
              <button @click="toggleDetail(s)" class="text-[11px] px-2 py-0.5 border rounded hover:bg-gray-50">
                {{ selectedScript?.id === s.id ? '收起' : '展开' }}
              </button>
              <button @click="handleGenerate(s)" :disabled="!hasRecording(s)" class="text-[11px] px-2 py-0.5 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-40 disabled:cursor-not-allowed">生成脚本</button>
              <button @click="handleRun(s)" :disabled="s.status !== 'READY'" class="text-[11px] px-2 py-0.5 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed">执行</button>
              <button @click="handleDelete(s.id)" class="text-[11px] px-2 py-0.5 bg-red-500 text-white rounded hover:bg-red-600">删除</button>
            </div>
          </div>

          <!-- Detail Panel -->
          <div v-if="selectedScript?.id === s.id" class="mt-4 border-t border-black/5 pt-4">
            <!-- Tabs -->
            <div class="flex gap-4 mb-3 border-b border-black/5">
              <button
                v-for="tab in detailTabs"
                :key="tab.key"
                @click="activeTab = tab.key"
                :class="activeTab === tab.key ? 'border-b-2 border-[#155DFC] text-[#155DFC]' : 'text-[#717182]'"
                class="text-[12px] pb-2 px-1"
              >{{ tab.label }}</button>
            </div>

            <!-- Recording Tab -->
            <div v-if="activeTab === 'recording'">
              <div class="flex items-center gap-2 mb-3">
                <button
                  @click="isRecording = !isRecording"
                  :class="isRecording ? 'bg-red-500' : 'bg-green-500'"
                  class="text-[11px] px-3 py-1 text-white rounded"
                >
                  {{ isRecording ? '停止录制' : '开始录制' }}
                </button>
                <button @click="handleSaveRecording" :disabled="recordedActions.length === 0" class="text-[11px] px-3 py-1 bg-[#155DFC] text-white rounded disabled:opacity-40">保存录制</button>
                <button @click="handleAddSampleAction" class="text-[11px] px-3 py-1 border rounded hover:bg-gray-50">添加示例操作</button>
                <span v-if="isRecording" class="text-[11px] text-red-500 animate-pulse">录制中...</span>
              </div>
              <div v-if="recordedActions.length === 0" class="text-[12px] text-[#717182] py-4 text-center">
                {{ hasRecording(s) ? '已有录制数据' : '暂无录制数据，点击"开始录制"或"添加示例操作"' }}
              </div>
              <div v-else class="space-y-1">
                <div v-for="(action, idx) in recordedActions" :key="idx" class="flex items-center gap-2 text-[11px] py-1 px-2 bg-gray-50 rounded">
                  <span class="font-mono text-[#155DFC]">{{ idx + 1 }}.</span>
                  <span class="font-medium">{{ action.type }}</span>
                  <span class="text-[#717182] font-mono truncate max-w-[300px]">{{ action.selector || action.value }}</span>
                  <button @click="recordedActions.splice(idx, 1)" class="ml-auto text-red-400 hover:text-red-600">x</button>
                </div>
              </div>
              <!-- Existing recording -->
              <div v-if="hasRecording(s) && recordedActions.length === 0" class="mt-2">
                <div class="text-[11px] text-[#717182] mb-1">已保存的录制 ({{ ((s.recordingJson as any)?.actions || []).length }} 步):</div>
                <div v-for="(action, idx) in ((s.recordingJson as any)?.actions || [])" :key="idx" class="flex items-center gap-2 text-[11px] py-1 px-2 bg-gray-50 rounded">
                  <span class="font-mono text-[#155DFC]">{{ idx + 1 }}.</span>
                  <span class="font-medium">{{ action.type }}</span>
                  <span class="text-[#717182] font-mono truncate max-w-[300px]">{{ action.selector || action.value }}</span>
                </div>
              </div>
            </div>

            <!-- Script Tab -->
            <div v-if="activeTab === 'script'">
              <div v-if="s.scriptContent" class="bg-gray-900 text-green-400 text-[11px] font-mono p-4 rounded overflow-x-auto max-h-[400px] overflow-y-auto">
                <pre>{{ s.scriptContent }}</pre>
              </div>
              <div v-else class="text-[12px] text-[#717182] py-4 text-center">
                尚未生成脚本。请先录制操作，然后点击"生成脚本"。
              </div>
            </div>

            <!-- Runs Tab -->
            <div v-if="activeTab === 'runs'">
              <div v-if="scriptRuns.length === 0" class="text-[12px] text-[#717182] py-4 text-center">暂无执行记录</div>
              <table v-else class="w-full text-[12px]">
                <thead>
                  <tr class="border-b border-black/5">
                    <th class="text-left py-2 px-2 text-[#717182] font-medium">运行ID</th>
                    <th class="text-left py-2 px-2 text-[#717182] font-medium">状态</th>
                    <th class="text-left py-2 px-2 text-[#717182] font-medium">步骤</th>
                    <th class="text-left py-2 px-2 text-[#717182] font-medium">耗时</th>
                    <th class="text-left py-2 px-2 text-[#717182] font-medium">时间</th>
                    <th class="text-left py-2 px-2 text-[#717182] font-medium">错误</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in scriptRuns" :key="r.id" class="border-b border-black/5">
                    <td class="py-2 px-2 font-mono text-[11px]">{{ r.id.slice(0, 8) }}...</td>
                    <td class="py-2 px-2"><span :class="runStatusClass(r.status)" class="px-2 py-0.5 rounded text-[11px]">{{ r.status }}</span></td>
                    <td class="py-2 px-2">{{ r.stepsPassed }}/{{ r.stepsTotal }}</td>
                    <td class="py-2 px-2">{{ r.durationMs ? r.durationMs + 'ms' : '-' }}</td>
                    <td class="py-2 px-2">{{ r.startedAt || '-' }}</td>
                    <td class="py-2 px-2 text-red-500 max-w-[200px] truncate">{{ r.errorMessage || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Screenshots Tab -->
            <div v-if="activeTab === 'screenshots'">
              <div v-if="!latestRun || latestRun.screenshotPaths.length === 0" class="text-[12px] text-[#717182] py-4 text-center">
                暂无截图
              </div>
              <div v-else class="grid grid-cols-3 gap-3">
                <div v-for="(path, idx) in latestRun.screenshotPaths" :key="idx" class="border rounded overflow-hidden">
                  <div class="text-[11px] text-[#717182] p-2 bg-gray-50 truncate">{{ path }}</div>
                  <div class="h-[200px] bg-gray-100 flex items-center justify-center text-[11px] text-[#717182]">截图预览</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Global Runs -->
      <div class="mt-6">
        <div class="text-[14px] font-semibold mb-3">全部执行记录</div>
        <div v-if="allRuns.length === 0" class="text-[12px] text-[#717182]">暂无执行记录</div>
        <table v-else class="w-full text-[12px]">
          <thead>
            <tr class="border-b border-black/5">
              <th class="text-left py-2 px-2 text-[#717182] font-medium">运行ID</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">脚本ID</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">状态</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">步骤</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">耗时</th>
              <th class="text-left py-2 px-2 text-[#717182] font-medium">时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in allRuns" :key="r.id" class="border-b border-black/5">
              <td class="py-2 px-2 font-mono text-[11px]">{{ r.id.slice(0, 8) }}...</td>
              <td class="py-2 px-2 font-mono text-[11px]">{{ r.scriptId.slice(0, 8) }}...</td>
              <td class="py-2 px-2"><span :class="runStatusClass(r.status)" class="px-2 py-0.5 rounded text-[11px]">{{ r.status }}</span></td>
              <td class="py-2 px-2">{{ r.stepsPassed }}/{{ r.stepsTotal }}</td>
              <td class="py-2 px-2">{{ r.durationMs ? r.durationMs + 'ms' : '-' }}</td>
              <td class="py-2 px-2">{{ r.startedAt || '-' }}</td>
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
import {
  listScripts, createScript, deleteScript, generateScript, runTest,
  saveRecording, listRuns,
  type UiTestScript, type UiTestRun,
} from '@/lib/api/uiAutomation'

const route = useRoute()
const projectId = route.params.projectId as string

const scripts = ref<UiTestScript[]>([])
const allRuns = ref<UiTestRun[]>([])
const scriptRuns = ref<UiTestRun[]>([])
const loading = ref(false)
const showCreate = ref(false)
const selectedScript = ref<UiTestScript | null>(null)
const activeTab = ref('recording')
const isRecording = ref(false)
const recordedActions = ref<Record<string, unknown>[]>([])
const latestRun = ref<UiTestRun | null>(null)

const createForm = ref({
  name: '',
  description: '',
  browser: 'chromium',
  viewportWidth: 1280,
  viewportHeight: 720,
  baseUrl: '',
})

const detailTabs = [
  { key: 'recording', label: '录制操作' },
  { key: 'script', label: '生成脚本' },
  { key: 'runs', label: '执行记录' },
  { key: 'screenshots', label: '截图' },
]

const statusClass = (s: string) => ({
  DRAFT: 'bg-gray-100 text-gray-600',
  RECORDED: 'bg-blue-100 text-blue-700',
  READY: 'bg-green-100 text-green-700',
  RUNNING: 'bg-yellow-100 text-yellow-700',
  PASSED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
  ERROR: 'bg-red-100 text-red-700',
})[s] || 'bg-gray-100'

const runStatusClass = (s: string) => ({
  QUEUED: 'bg-gray-100 text-gray-600',
  RUNNING: 'bg-blue-100 text-blue-700',
  PASSED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
  ERROR: 'bg-red-100 text-red-700',
})[s] || 'bg-gray-100'

function hasRecording(s: UiTestScript): boolean {
  const actions = (s.recordingJson as any)?.actions
  return Array.isArray(actions) && actions.length > 0
}

async function load() {
  loading.value = true
  try {
    const [sRes, rRes] = await Promise.all([
      listScripts(projectId),
      listRuns(projectId),
    ])
    scripts.value = sRes.items
    allRuns.value = rRes.items
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createForm.value.name) return
  await createScript(projectId, createForm.value)
  showCreate.value = false
  createForm.value = { name: '', description: '', browser: 'chromium', viewportWidth: 1280, viewportHeight: 720, baseUrl: '' }
  await load()
}

async function handleDelete(id: string) {
  await deleteScript(projectId, id)
  if (selectedScript.value?.id === id) selectedScript.value = null
  await load()
}

async function toggleDetail(s: UiTestScript) {
  if (selectedScript.value?.id === s.id) {
    selectedScript.value = null
    return
  }
  selectedScript.value = s
  activeTab.value = 'recording'
  recordedActions.value = []
  await loadScriptRuns(s.id)
}

async function loadScriptRuns(scriptId: string) {
  const res = await listRuns(projectId, scriptId)
  scriptRuns.value = res.items
  latestRun.value = res.items.length > 0 ? res.items[0] : null
}

function handleAddSampleAction() {
  recordedActions.value.push({ type: 'click', selector: '#button-id', value: '' })
  recordedActions.value.push({ type: 'fill', selector: '#input-field', value: 'test value' })
  recordedActions.value.push({ type: 'assert', selector: '.result', value: 'toBeVisible()' })
}

async function handleSaveRecording() {
  if (!selectedScript.value || recordedActions.value.length === 0) return
  await saveRecording(projectId, selectedScript.value.id, recordedActions.value)
  recordedActions.value = []
  await load()
  if (selectedScript.value) {
    selectedScript.value = scripts.value.find(s => s.id === selectedScript.value?.id) || null
  }
}

async function handleGenerate(s: UiTestScript) {
  await generateScript(projectId, s.id)
  await load()
  if (selectedScript.value?.id === s.id) {
    selectedScript.value = scripts.value.find(sc => sc.id === s.id) || null
  }
}

async function handleRun(s: UiTestScript) {
  await runTest(projectId, s.id)
  await load()
  if (selectedScript.value?.id === s.id) {
    await loadScriptRuns(s.id)
  }
}

onMounted(load)
</script>
