<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">性能测试平台</div>
          <div class="text-[12px] text-[#717182] mt-1">管理 k6 性能测试，支持负载、压力、峰值和浸泡测试</div>
        </div>
        <div class="flex gap-2">
          <button @click="showK6Gen = true" class="text-[12px] px-3 py-1 border border-[#155DFC] text-[#155DFC] rounded hover:bg-blue-50">生成 k6 脚本</button>
          <button @click="showCreate = true" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded hover:bg-blue-700">新建测试</button>
        </div>
      </div>

      <!-- Create form -->
      <div v-if="showCreate" class="mb-4 p-4 border border-black/10 rounded bg-gray-50">
        <div class="text-[13px] font-medium mb-2">新建性能测试</div>
        <div class="grid grid-cols-2 gap-3">
          <input v-model="form.name" placeholder="测试名称" class="text-[12px] border rounded px-2 py-1" />
          <select v-model="form.testType" class="text-[12px] border rounded px-2 py-1">
            <option value="LOAD">负载测试 (LOAD)</option>
            <option value="STRESS">压力测试 (STRESS)</option>
            <option value="SPIKE">峰值测试 (SPIKE)</option>
            <option value="SOAK">浸泡测试 (SOAK)</option>
          </select>
          <input v-model="form.targetUrl" placeholder="目标 URL" class="text-[12px] border rounded px-2 py-1 col-span-2" />
          <input v-model="form.description" placeholder="描述" class="text-[12px] border rounded px-2 py-1 col-span-2" />
        </div>
        <div class="mt-3">
          <div class="text-[11px] text-[#717182] mb-1">配置 (JSON: vus, duration, stages, thresholds)</div>
          <textarea v-model="configJson" rows="4" class="text-[11px] font-mono border rounded px-2 py-1 w-full" placeholder='{"vus": 10, "duration": "30s"}'></textarea>
        </div>
        <div class="flex gap-2 mt-3">
          <button @click="create" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded">创建</button>
          <button @click="showCreate = false" class="text-[12px] px-3 py-1 border rounded">取消</button>
        </div>
      </div>

      <!-- k6 Generator -->
      <div v-if="showK6Gen" class="mb-4 p-4 border border-black/10 rounded bg-gray-50">
        <div class="text-[13px] font-medium mb-2">生成 k6 脚本</div>
        <div class="grid grid-cols-2 gap-3">
          <select v-model="k6Form.testType" class="text-[12px] border rounded px-2 py-1">
            <option value="LOAD">负载测试</option>
            <option value="STRESS">压力测试</option>
            <option value="SPIKE">峰值测试</option>
            <option value="SOAK">浸泡测试</option>
          </select>
          <input v-model="k6Form.targetUrl" placeholder="目标 URL" class="text-[12px] border rounded px-2 py-1" />
        </div>
        <div class="mt-3">
          <div class="text-[11px] text-[#717182] mb-1">配置 (可选 JSON)</div>
          <textarea v-model="k6ConfigJson" rows="3" class="text-[11px] font-mono border rounded px-2 py-1 w-full" placeholder='{"vus": 10, "duration": "30s"}'></textarea>
        </div>
        <div class="flex gap-2 mt-3">
          <button @click="generateK6" class="text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded">生成</button>
          <button @click="showK6Gen = false; k6Script = ''" class="text-[12px] px-3 py-1 border rounded">关闭</button>
        </div>
        <div v-if="k6Script" class="mt-3">
          <div class="text-[11px] text-[#717182] mb-1">生成的 k6 脚本</div>
          <pre class="text-[11px] font-mono bg-[#1e1e1e] text-green-400 p-3 rounded overflow-x-auto max-h-[300px]">{{ k6Script }}</pre>
        </div>
      </div>

      <!-- Test List -->
      <div v-if="loading" class="text-center py-8 text-[12px] text-[#717182]">加载中...</div>
      <div v-else-if="tests.length === 0" class="text-center py-8 text-[12px] text-[#717182]">暂无性能测试</div>
      <div v-else class="space-y-3">
        <div v-for="t in tests" :key="t.id" class="border border-black/10 rounded p-4">
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <div class="text-[14px] font-medium">{{ t.name }}</div>
                <span :class="typeBadgeClass(t.testType)" class="px-2 py-0.5 rounded text-[10px] font-medium">{{ t.testType }}</span>
                <span :class="statusBadgeClass(t.status)" class="px-2 py-0.5 rounded text-[10px]">{{ t.status }}</span>
              </div>
              <div class="text-[11px] text-[#717182] mt-1">{{ t.targetUrl || '-' }} &middot; {{ t.description || '无描述' }}</div>
            </div>
            <div class="flex items-center gap-2">
              <button @click="executeTest(t.id)" class="text-[11px] px-2 py-0.5 bg-green-500 text-white rounded hover:bg-green-600">执行</button>
              <button @click="viewDetail(t)" class="text-[11px] px-2 py-0.5 bg-blue-500 text-white rounded hover:bg-blue-600">详情</button>
              <button @click="remove(t.id)" class="text-[11px] px-2 py-0.5 bg-red-500 text-white rounded hover:bg-red-600">删除</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail Panel -->
      <div v-if="selectedTest" class="mt-6">
        <div class="flex items-center justify-between mb-3">
          <div class="text-[14px] font-semibold">{{ selectedTest.name }} - 测试详情</div>
          <button @click="selectedTest = null; runs = []; trend = []" class="text-[11px] px-2 py-0.5 border rounded">关闭</button>
        </div>

        <!-- Metrics cards (latest run) -->
        <div v-if="latestRun" class="grid grid-cols-4 gap-3 mb-4">
          <div class="border border-black/10 rounded p-3 text-center">
            <div class="text-[11px] text-[#717182]">请求/秒</div>
            <div class="text-[18px] font-bold text-[#0A0A0A]">{{ latestRun.metrics.reqPerSec ?? '-' }}</div>
          </div>
          <div class="border border-black/10 rounded p-3 text-center">
            <div class="text-[11px] text-[#717182]">P95 延迟 (ms)</div>
            <div class="text-[18px] font-bold text-[#0A0A0A]">{{ latestRun.metrics.p95 ?? '-' }}</div>
          </div>
          <div class="border border-black/10 rounded p-3 text-center">
            <div class="text-[11px] text-[#717182]">P99 延迟 (ms)</div>
            <div class="text-[18px] font-bold text-[#0A0A0A]">{{ latestRun.metrics.p99 ?? '-' }}</div>
          </div>
          <div class="border border-black/10 rounded p-3 text-center">
            <div class="text-[11px] text-[#717182]">错误率 (%)</div>
            <div :class="toNum(latestRun.metrics.errorRate) > 5 ? 'text-red-600' : 'text-green-600'" class="text-[18px] font-bold">{{ latestRun.metrics.errorRate ?? '-' }}</div>
          </div>
        </div>

        <!-- Thresholds -->
        <div v-if="latestRun && latestRun.thresholds.details.length > 0" class="mb-4">
          <div class="text-[12px] font-medium mb-2">
            阈值检查
            <span :class="latestRun.thresholds.passed ? 'text-green-600' : 'text-red-600'" class="ml-2 text-[11px]">
              {{ latestRun.thresholds.passed ? '全部通过' : '未通过' }}
            </span>
          </div>
          <div class="space-y-1">
            <div v-for="d in latestRun.thresholds.details" :key="d.metric" class="flex items-center gap-2 text-[11px]">
              <span :class="d.passed ? 'text-green-500' : 'text-red-500'">{{ d.passed ? '[PASS]' : '[FAIL]' }}</span>
              <span class="font-medium">{{ d.metric }}</span>
              <span class="text-[#717182]">= {{ d.value }}</span>
              <span class="text-[#717182]">({{ d.rules.join(', ') }})</span>
            </div>
          </div>
        </div>

        <!-- k6 Script Preview -->
        <div v-if="selectedTest.scriptContent" class="mb-4">
          <div class="text-[12px] font-medium mb-2">k6 脚本</div>
          <pre class="text-[11px] font-mono bg-[#1e1e1e] text-green-400 p-3 rounded overflow-x-auto max-h-[200px]">{{ selectedTest.scriptContent }}</pre>
        </div>

        <!-- Trend Table -->
        <div v-if="trend.length > 0" class="mb-4">
          <div class="text-[12px] font-medium mb-2">趋势数据</div>
          <table class="w-full text-[11px]">
            <thead>
              <tr class="border-b border-black/5">
                <th class="text-left py-2 px-2 text-[#717182] font-medium">时间</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">请求/秒</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">平均延迟</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">P95</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">P99</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">错误率</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">耗时(ms)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tp in trend" :key="tp.runId" class="border-b border-black/5">
                <td class="py-2 px-2">{{ formatDate(tp.createdAt) }}</td>
                <td class="py-2 px-2">{{ tp.reqPerSec ?? '-' }}</td>
                <td class="py-2 px-2">{{ tp.avgLatency ?? '-' }} ms</td>
                <td class="py-2 px-2">{{ tp.p95 ?? '-' }} ms</td>
                <td class="py-2 px-2">{{ tp.p99 ?? '-' }} ms</td>
                <td class="py-2 px-2" :class="(tp.errorRate ?? 0) > 5 ? 'text-red-600' : ''">{{ tp.errorRate ?? '-' }}%</td>
                <td class="py-2 px-2">{{ tp.durationMs ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Runs Table -->
        <div class="mt-4">
          <div class="text-[12px] font-medium mb-2">执行记录</div>
          <div v-if="runs.length === 0" class="text-[11px] text-[#717182]">暂无执行记录</div>
          <table v-else class="w-full text-[11px]">
            <thead>
              <tr class="border-b border-black/5">
                <th class="text-left py-2 px-2 text-[#717182] font-medium">运行ID</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">状态</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">请求/秒</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">P95</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">错误率</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">阈值</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">耗时</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in runs" :key="r.id" class="border-b border-black/5">
                <td class="py-2 px-2 font-mono">{{ r.id.slice(0, 8) }}...</td>
                <td class="py-2 px-2">
                  <span :class="runStatusClass(r.status)" class="px-2 py-0.5 rounded text-[10px]">{{ r.status }}</span>
                </td>
                <td class="py-2 px-2">{{ r.metrics.reqPerSec ?? '-' }}</td>
                <td class="py-2 px-2">{{ r.metrics.p95 ?? '-' }} ms</td>
                <td class="py-2 px-2" :class="toNum(r.metrics.errorRate) > 5 ? 'text-red-600' : ''">{{ r.metrics.errorRate ?? '-' }}%</td>
                <td class="py-2 px-2">
                  <span :class="r.thresholds.passed ? 'text-green-600' : 'text-red-600'" class="text-[10px] font-medium">
                    {{ r.thresholds.passed ? 'PASS' : 'FAIL' }}
                  </span>
                </td>
                <td class="py-2 px-2">{{ r.durationMs ? r.durationMs + 'ms' : '-' }}</td>
                <td class="py-2 px-2">{{ formatDate(r.createdAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  listPerformanceTests,
  createPerformanceTest,
  deletePerformanceTest,
  runPerformanceTest,
  listPerformanceTestRuns,
  getPerformanceTestTrend,
  generateK6Script,
  type PerformanceTest,
  type PerformanceTestRun,
  type TrendDataPoint,
} from '@/lib/api/performanceTests'

const route = useRoute()
const projectId = route.params.projectId as string

const tests = ref<PerformanceTest[]>([])
const runs = ref<PerformanceTestRun[]>([])
const trend = ref<TrendDataPoint[]>([])
const loading = ref(false)
const showCreate = ref(false)
const showK6Gen = ref(false)
const selectedTest = ref<PerformanceTest | null>(null)
const configJson = ref('')
const k6ConfigJson = ref('')
const k6Script = ref('')

const form = ref({
  name: '',
  testType: 'LOAD',
  targetUrl: '',
  description: '',
})

const k6Form = ref({
  testType: 'LOAD',
  targetUrl: '',
})

const latestRun = computed(() => {
  if (runs.value.length === 0) return null
  return runs.value[0]
})

function toNum(v: unknown): number {
  if (typeof v === 'number') return v
  if (typeof v === 'string') return Number(v) || 0
  return 0
}

const typeBadgeClass = (type: string) =>
  ({
    LOAD: 'bg-blue-100 text-blue-700',
    STRESS: 'bg-orange-100 text-orange-700',
    SPIKE: 'bg-red-100 text-red-700',
    SOAK: 'bg-purple-100 text-purple-700',
  })[type] || 'bg-gray-100 text-gray-600'

const statusBadgeClass = (status: string) =>
  ({
    DRAFT: 'bg-gray-100 text-gray-600',
    ACTIVE: 'bg-green-100 text-green-700',
    ARCHIVED: 'bg-yellow-100 text-yellow-700',
  })[status] || 'bg-gray-100'

const runStatusClass = (s: string) =>
  ({
    QUEUED: 'bg-yellow-100 text-yellow-700',
    RUNNING: 'bg-blue-100 text-blue-700',
    COMPLETED: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-100 text-red-700',
  })[s] || 'bg-gray-100'

const formatDate = (ts: number) => new Date(ts * 1000).toLocaleString('zh-CN')

async function load() {
  loading.value = true
  try {
    const res = await listPerformanceTests(projectId)
    tests.value = res.items
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.value.name) return
  let config: Record<string, unknown> | undefined
  if (configJson.value.trim()) {
    try {
      config = JSON.parse(configJson.value)
    } catch {
      alert('配置 JSON 格式错误')
      return
    }
  }
  await createPerformanceTest(projectId, {
    name: form.value.name,
    testType: form.value.testType,
    targetUrl: form.value.targetUrl,
    description: form.value.description,
    config,
  })
  showCreate.value = false
  form.value = { name: '', testType: 'LOAD', targetUrl: '', description: '' }
  configJson.value = ''
  await load()
}

async function remove(id: string) {
  await deletePerformanceTest(projectId, id)
  if (selectedTest.value?.id === id) {
    selectedTest.value = null
    runs.value = []
    trend.value = []
  }
  await load()
}

async function executeTest(testId: string) {
  await runPerformanceTest(projectId, testId)
  if (selectedTest.value?.id === testId) {
    await loadDetail(testId)
  }
}

async function viewDetail(t: PerformanceTest) {
  selectedTest.value = t
  await loadDetail(t.id)
}

async function loadDetail(testId: string) {
  const [runsRes, trendRes] = await Promise.all([
    listPerformanceTestRuns(projectId, testId),
    getPerformanceTestTrend(projectId, testId),
  ])
  runs.value = runsRes.items
  trend.value = trendRes
}

async function generateK6() {
  if (!k6Form.value.targetUrl) return
  let config: Record<string, unknown> | undefined
  if (k6ConfigJson.value.trim()) {
    try {
      config = JSON.parse(k6ConfigJson.value)
    } catch {
      alert('配置 JSON 格式错误')
      return
    }
  }
  const res = await generateK6Script(projectId, {
    testType: k6Form.value.testType,
    targetUrl: k6Form.value.targetUrl,
    config,
  })
  k6Script.value = res.script
}

onMounted(load)
</script>
