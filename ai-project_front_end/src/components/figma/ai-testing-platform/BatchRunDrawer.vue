<script setup lang="ts">
import { computed } from 'vue'
import type { Row } from '@/components/figma/ai-testing-platform/CasesTable.vue'

const props = defineProps<{
  isOpen: boolean
  rows: Row[]
  state: 'preview' | 'executing' | 'completed'
  canGenerateReport: boolean
  runId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'execute'): void
  (e: 'generate-report'): void
}>()

const executeButtonLabel = computed(() => (props.state === 'executing' ? '执行中...' : '执行'))

function formatApiParams(apiParams: Row['apiParams']) {
  if (!apiParams || typeof apiParams !== 'object' || Array.isArray(apiParams)) return '-'
  const keys = Object.keys(apiParams)
  if (!keys.length) return '-'
  try {
    return JSON.stringify(apiParams)
  } catch {
    return '-'
  }
}

function formatExpectedResult(expectedResult: Row['expectedResult']) {
  const value = String(expectedResult || '').trim()
  return value || '-'
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50">
    <div class="absolute inset-0 bg-black/30" @click="emit('close')"></div>
    <aside class="absolute right-0 top-0 h-full w-[860px] max-w-[calc(100vw-24px)] border-l border-black/10 bg-white shadow-[-12px_0_32px_rgba(0,0,0,0.12)]">
      <div class="flex h-full flex-col">
        <div class="flex items-center justify-between border-b border-black/10 px-[20px] py-[16px]">
          <div>
            <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">批量执行</div>
            <div class="text-[12px] leading-[16px] text-[#717182]">共 {{ rows.length }} 条用例</div>
          </div>
          <button type="button" class="h-[28px] w-[28px] rounded-[8px] text-[16px] leading-[20px] text-[#717182]" @click="emit('close')">
            ×
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-auto px-[20px] py-[16px]">
          <div class="w-full overflow-x-auto rounded-[12px] border border-black/10">
            <div class="min-w-[1320px]">
              <div class="grid grid-cols-[160px_minmax(200px,1fr)_100px_260px_300px_300px] border-b border-black/10 bg-[rgba(236,236,240,0.3)]">
                <div class="px-[12px] py-[10px] text-[12px] font-medium leading-[16px] text-[#717182]">功能模块</div>
                <div class="px-[12px] py-[10px] text-[12px] font-medium leading-[16px] text-[#717182]">标题</div>
                <div class="px-[12px] py-[10px] text-[12px] font-medium leading-[16px] text-[#717182]">调用方式</div>
                <div class="px-[12px] py-[10px] text-[12px] font-medium leading-[16px] text-[#717182]">interfaceUrl</div>
                <div class="px-[12px] py-[10px] text-[12px] font-medium leading-[16px] text-[#717182]">接口参数</div>
                <div class="px-[12px] py-[10px] text-[12px] font-medium leading-[16px] text-[#717182]">预期结果</div>
              </div>
              <div
                v-for="row in rows"
                :key="row.id"
                class="grid grid-cols-[160px_minmax(200px,1fr)_100px_260px_300px_300px] border-b border-black/10 last:border-b-0"
              >
                <div class="truncate px-[12px] py-[12px] text-[12px] leading-[16px] text-[#717182]" :title="row.module || '-'">
                  {{ row.module || '-' }}
                </div>
                <div class="truncate px-[12px] py-[12px] text-[13px] leading-[18px] text-[#0A0A0A]" :title="row.title">
                  {{ row.title }}
                </div>
                <div class="px-[12px] py-[12px] text-[12px] font-medium leading-[16px] text-[#717182]">
                  {{ row.method || '-' }}
                </div>
                <div class="truncate px-[12px] py-[12px] text-[12px] leading-[16px] text-[#155DFC]" :title="row.interfaceUrl || '-'">
                  {{ row.interfaceUrl || '-' }}
                </div>
                <div class="truncate px-[12px] py-[12px] text-[12px] leading-[16px] text-[#717182]" :title="formatApiParams(row.apiParams)">
                  {{ formatApiParams(row.apiParams) }}
                </div>
                <div class="truncate px-[12px] py-[12px] text-[12px] leading-[16px] text-[#717182]" :title="formatExpectedResult(row.expectedResult)">
                  {{ formatExpectedResult(row.expectedResult) }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between border-t border-black/10 px-[20px] py-[12px]">
          <div class="text-[12px] leading-[16px] text-[#717182]">
            <span v-if="runId">runId：{{ runId }}</span>
            <span v-else>尚未执行</span>
          </div>
          <div class="flex items-center gap-[8px]">
            <button
              type="button"
              class="h-[32px] rounded-[10px] border border-black/10 px-[14px] text-[14px] font-medium leading-[20px] text-[#717182]"
              @click="emit('close')"
            >
              取消
            </button>
            <button
              type="button"
              class="h-[32px] rounded-[10px] bg-[#155DFC] px-[14px] text-[14px] font-medium leading-[20px] text-white disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="state === 'executing'"
              @click="emit('execute')"
            >
              {{ executeButtonLabel }}
            </button>
            <button
              type="button"
              class="h-[32px] rounded-[10px] border border-[#BEDBFF] px-[14px] text-[14px] font-medium leading-[20px] text-[#155DFC] disabled:cursor-not-allowed disabled:border-black/10 disabled:text-[#A1A1AA]"
              :disabled="!canGenerateReport"
              @click="emit('generate-report')"
            >
              生成报告
            </button>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>
