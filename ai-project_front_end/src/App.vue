<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const toastMessage = ref('')
const isToastVisible = ref(false)
const toastType = ref<'success' | 'error'>('success')
let toastTimer: number | null = null

function showToast(message: string, type: 'success' | 'error' = 'success') {
  toastMessage.value = message
  toastType.value = type
  isToastVisible.value = true
  if (toastTimer) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => {
    isToastVisible.value = false
    toastTimer = null
  }, 1500)
}

function onToastEvent(e: Event) {
  const payload = (e as CustomEvent).detail as { message?: string; type?: 'success' | 'error' } | undefined
  const message = payload?.message
  if (!message) return
  showToast(message, payload?.type ?? 'success')
}

onMounted(() => {
  window.addEventListener('app-toast', onToastEvent as EventListener)
})

onBeforeUnmount(() => {
  window.removeEventListener('app-toast', onToastEvent as EventListener)
  if (toastTimer) window.clearTimeout(toastTimer)
})
</script>

<template>
  <router-view />
  <div v-if="isToastVisible" class="fixed left-1/2 top-[16px] z-[80] -translate-x-1/2">
    <div
      :class="[
        'flex items-center gap-[8px] rounded-[12px] px-[14px] py-[10px] text-[14px] leading-[20px] shadow-[0px_12px_20px_-6px_rgba(0,0,0,0.15),0px_6px_10px_-6px_rgba(0,0,0,0.12)] border',
        toastType === 'success'
          ? 'bg-[#ECFDF5] border-[#BBF7D0] text-[#065F46]'
          : 'bg-[#FEF2F2] border-[#FECACA] text-[#991B1B]'
      ]"
    >
      <span
        :class="[
          'flex h-[20px] w-[20px] items-center justify-center rounded-full',
          toastType === 'success' ? 'bg-[#D1FAE5]' : 'bg-[#FEE2E2]'
        ]"
      >
        <svg v-if="toastType === 'success'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" class="h-[12px] w-[12px]" fill="currentColor">
          <path
            d="M16.707 5.293a1 1 0 0 1 0 1.414l-7.25 7.25a1 1 0 0 1-1.414 0l-3-3a1 1 0 1 1 1.414-1.414L8.5 11.586l6.543-6.543a1 1 0 0 1 1.414 0Z"
          />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" class="h-[12px] w-[12px]" fill="currentColor">
          <path d="M10 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm-1-5a1 1 0 1 0 2 0 1 1 0 0 0-2 0Zm0-6v4a1 1 0 1 0 2 0V7a1 1 0 1 0-2 0Z" />
        </svg>
      </span>
      <span>{{ toastMessage }}</span>
    </div>
  </div>
</template>
