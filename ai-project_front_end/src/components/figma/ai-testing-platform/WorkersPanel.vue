<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import workersRefresh from '@/assets/figma/ai-testing-platform-workers/workers-refresh.svg'
import workersRegister from '@/assets/figma/ai-testing-platform-workers/workers-register.svg'
import WorkerCard, { type WorkerCardData } from '@/components/figma/ai-testing-platform/WorkerCard.vue'
import { fetchWorkers, type WorkerAdminListItem } from '@/lib/api/workers'

const isLoading = ref(false)
const error = ref('')
const workers = ref<WorkerAdminListItem[]>([])

const onlineCount = computed(() => workers.value.filter((worker) => worker.status === 'ONLINE').length)
const offlineCount = computed(() => workers.value.filter((worker) => worker.status === 'OFFLINE').length)
const totalSlots = computed(() => workers.value.reduce((sum, worker) => sum + Number(worker.slots || 0), 0))

const stats = computed(() => [
  { value: String(onlineCount.value), label: '在线 Workers', valueColor: '#00A63E', bg: '#F0FDF4' },
  { value: String(totalSlots.value), label: '总并发槽位', valueColor: '#155DFC', bg: '#EFF6FF' },
  { value: String(offlineCount.value), label: '离线 Workers', valueColor: '#9810FA', bg: '#FAF5FF' }
])

function formatLastSeen(lastSeenAt?: number | null) {
  if (!lastSeenAt) return '最近心跳：暂无'
  const diffSec = Math.max(0, Math.floor((Date.now() - lastSeenAt * 1000) / 1000))
  if (diffSec < 60) return `最近心跳：${diffSec}s前`
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `最近心跳：${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `最近心跳：${diffHour}小时前`
  return `最近心跳：${Math.floor(diffHour / 24)}天前`
}

function mapWorker(worker: WorkerAdminListItem): WorkerCardData {
  const isOnline = worker.status === 'ONLINE'
  return {
    name: worker.name,
    status: isOnline ? '在线' : '离线',
    version: worker.version || '-',
    capabilities: worker.capabilities,
    slotsText: isOnline ? `${worker.slots}/${worker.slots}` : `0/${worker.slots}`,
    slotsStateText: isOnline ? '总槽位' : '不可用',
    heartbeatText: formatLastSeen(worker.lastSeenAt),
    isFaded: !isOnline,
    borderColor: isOnline ? undefined : '#FFC9C9'
  }
}

const workerCards = computed(() => workers.value.map(mapWorker))

async function loadWorkers() {
  isLoading.value = true
  error.value = ''
  try {
    const data = await fetchWorkers({ page: 1, pageSize: 200 })
    workers.value = data.items
  } catch (err) {
    workers.value = []
    error.value = err instanceof Error ? err.message : 'Worker 列表加载失败'
  } finally {
    isLoading.value = false
  }
}

function showRegisterHint() {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message: 'Worker 注册请调用 /api/workers/register 获取 token', type: 'success' } }))
}

onMounted(() => {
  void loadWorkers()
})
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)]">
    <div class="flex flex-col gap-[16px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="flex flex-col gap-[12px] md:flex-row md:items-center md:justify-between md:gap-0">
        <div class="flex flex-col gap-[2px]">
          <div class="text-[18px] font-semibold leading-[28px] text-[#0A0A0A]">Worker 管理</div>
          <div class="text-[14px] leading-[20px] text-[#717182]">
            {{ isLoading ? '正在刷新执行节点状态...' : '执行节点状态与资源监控' }}
          </div>
        </div>

        <div class="flex items-center gap-[8px]">
          <button
            type="button"
            class="relative h-[32px] w-[72.33px] rounded-[10px] border border-black/10 bg-transparent disabled:opacity-50"
            :disabled="isLoading"
            @click="loadWorkers"
          >
            <img :src="workersRefresh" alt="" class="absolute left-[12.67px] top-[9.5px] h-[13px] w-[13px]" />
            <span class="absolute left-[29.67px] top-[6.33px] text-[14px] font-medium leading-[20px] text-[#717182]"> 刷新</span>
          </button>

          <button type="button" class="relative h-[32px] w-[124.89px] rounded-[10px] bg-[#155DFC]" @click="showRegisterHint">
            <img :src="workersRegister" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
            <span class="absolute left-[30px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
              注册 Worker
            </span>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-[16px] md:grid-cols-3">
        <div
          v-for="item in stats"
          :key="item.label"
          class="h-[84px] w-full max-w-[325.33px] rounded-[14px] px-[16px] pt-[16px]"
          :style="{ background: item.bg }"
        >
          <div class="text-[24px] font-semibold leading-[32px]" :style="{ color: item.valueColor }">{{ item.value }}</div>
          <div class="mt-[4px] text-[12px] leading-[16px] text-[#717182]">{{ item.label }}</div>
        </div>
      </div>

      <div v-if="error" class="rounded-[12px] border border-[#FFC9C9] bg-[#FFF5F5] px-4 py-3 text-[13px] text-[#C10007]">
        {{ error }}
      </div>

      <div v-else-if="!isLoading && workerCards.length === 0" class="rounded-[14px] border border-dashed border-black/10 bg-white px-6 py-10 text-center">
        <div class="text-[14px] font-semibold text-[#0A0A0A]">暂无 Worker</div>
        <div class="mt-2 text-[12px] text-[#717182]">注册 Worker 后，这里会展示节点能力、状态、槽位和最近心跳。</div>
      </div>

      <div v-else class="grid grid-cols-1 gap-[16px] md:grid-cols-2 lg:grid-cols-3">
        <WorkerCard v-for="w in workerCards" :key="w.name" :data="w" />
      </div>
    </div>
  </div>
</template>
