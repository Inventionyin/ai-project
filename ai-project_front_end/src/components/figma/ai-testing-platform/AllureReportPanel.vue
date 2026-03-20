<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const runId = computed(() => {
  const raw = route.query.runId
  if (typeof raw === 'string') return raw.trim()
  if (Array.isArray(raw) && typeof raw[0] === 'string') return raw[0].trim()
  return ''
})

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const iframeSrc = computed(() => {
  if (!runId.value) return ''
  const token = String(localStorage.getItem('accessToken') || '').trim()
  const base = resolveApiBaseUrl()
  const params = new URLSearchParams()
  if (token) params.set('access_token', token)
  const queryText = params.toString()
  const suffix = queryText ? `?${queryText}` : ''
  return `${base}/api/runs/${encodeURIComponent(runId.value)}/allure-report/${suffix}`
})
</script>

<template>
  <div class="w-full bg-[rgba(236,236,240,0.3)] md:pr-[16.67px]">
    <div class="flex flex-col gap-[12px] px-[16px] pt-[16px] md:px-[24px] md:pt-[24px]">
      <div class="rounded-[12px] border border-black/10 bg-white px-[16px] py-[12px]">
        <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">Allure报告</div>
        <div class="text-[12px] leading-[16px] text-[#717182]">{{ runId ? `runId：${runId}` : '缺少 runId，请先完成批量执行再生成报告' }}</div>
      </div>
      <div v-if="iframeSrc" class="overflow-hidden rounded-[12px] border border-black/10 bg-white">
        <iframe
          :key="iframeSrc"
          :src="iframeSrc"
          class="h-[calc(100vh-176px)] w-full border-0"
          title="Allure报告"
          loading="lazy"
          referrerpolicy="no-referrer"
        ></iframe>
      </div>
      <div v-else class="rounded-[12px] border border-dashed border-black/10 bg-white px-[16px] py-[18px] text-[13px] leading-[20px] text-[#717182]">
        暂无可展示的 Allure 报告
      </div>
    </div>
  </div>
</template>
