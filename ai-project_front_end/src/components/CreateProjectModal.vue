<script setup lang="ts">
import { ref } from 'vue'

const { isOpen } = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'create', data: { name: string; description: string }): void
}>()

const formData = ref({
  name: '',
  description: ''
})

const errorMessage = ref('')

const handleClose = () => {
  errorMessage.value = ''
  emit('close')
}

const handleCreate = () => {
  const name = formData.value.name.trim()
  
  if (name.length < 2 || name.length > 50) {
    errorMessage.value = '请输入项目名称，长度为2-50个字符'
    return
  }
  
  errorMessage.value = ''
  emit('create', { ...formData.value, name }) // Use trimmed name
  // Reset form
  formData.value.name = ''
  formData.value.description = ''
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Overlay -->
    <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="handleClose"></div>

    <!-- Modal Container -->
    <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-[448px] mx-4 flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
      
      <!-- Header -->
      <div class="px-6 pt-6 pb-0">
        <h2 class="text-base font-semibold text-[#0A0A0A] leading-6">新建项目</h2>
      </div>

      <!-- Body -->
      <div class="p-6 flex flex-col gap-4">
        
        <!-- Project Name Input -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#0A0A0A] leading-5">
            项目名称 <span class="text-red-500">*</span>
          </label>
          <div class="relative">
            <input 
              v-model="formData.name"
              type="text" 
              placeholder="2-50个字符"
              :class="[
                'w-full h-[38px] px-3 py-2 bg-white border rounded-[10px] text-sm text-[#0A0A0A] placeholder:text-[#0A0A0A]/40 focus:outline-none focus:ring-2 transition-all',
                errorMessage ? 'border-red-500 focus:ring-red-500/20 focus:border-red-500' : 'border-black/10 focus:ring-[#155DFC]/20 focus:border-[#155DFC]'
              ]"
              @input="errorMessage = ''"
            />
          </div>
          <span v-if="errorMessage" class="text-xs text-red-500 mt-1">{{ errorMessage }}</span>
        </div>

        <!-- Description Textarea -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#0A0A0A] leading-5">
            描述
          </label>
          <div class="relative">
            <textarea 
              v-model="formData.description"
              placeholder="可选，0-200个字符"
              class="w-full h-[84px] px-3 py-2 bg-white border border-black/10 rounded-[10px] text-sm text-[#0A0A0A] placeholder:text-[#0A0A0A]/40 focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 focus:border-[#155DFC] resize-none transition-all"
            ></textarea>
          </div>
        </div>

      </div>

      <!-- Footer -->
      <div class="px-6 pb-6 pt-0 flex gap-2">
        <button 
          @click="handleClose"
          class="flex-1 h-9 px-3 py-1.5 bg-white border border-black/10 rounded-[10px] text-sm font-medium text-[#0A0A0A] hover:bg-gray-50 active:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-200"
        >
          取消
        </button>
        <button 
          @click="handleCreate"
          class="flex-1 h-9 px-3 py-1.5 bg-[#155DFC] border border-transparent rounded-[10px] text-sm font-medium text-white hover:bg-[#155DFC]/90 active:bg-[#155DFC] transition-colors focus:outline-none focus:ring-2 focus:ring-[#155DFC]/20 shadow-sm"
        >
          创建
        </button>
      </div>

    </div>
  </div>
</template>
