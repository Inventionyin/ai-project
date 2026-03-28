<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface ProjectData {
  id: string
  title: string
  description: string
}

const props = defineProps<{
  isOpen: boolean
  project: ProjectData | null
  isSaving?: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', data: { name: string; description: string }): void
}>()

const name = ref('')
const description = ref('')

const isEditMode = computed(() => !!props.project)
const canSubmit = computed(() => name.value.trim().length > 0 && !props.isSaving)

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    if (props.project) {
      name.value = props.project.title
      description.value = props.project.description
    } else {
      name.value = ''
      description.value = ''
    }
  }
})

const handleSave = () => {
  if (!canSubmit.value) return
  emit('save', { name: name.value, description: description.value })
}

const handleClose = () => {
  emit('close')
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" @click.self="handleClose">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
      <div class="p-6">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-xl font-bold text-gray-900">{{ isEditMode ? '编辑项目' : '新建项目' }}</h2>
          <button @click="handleClose" class="text-gray-400 hover:text-gray-600">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <form @submit.prevent="handleSave">
          <div class="space-y-4">
            <div>
              <label for="projectName" class="block text-sm font-medium text-gray-700">项目名称</label>
              <input v-model="name" type="text" id="projectName" :disabled="props.isSaving" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:bg-gray-100 disabled:text-gray-500" required>
            </div>
            <div>
              <label for="projectDescription" class="block text-sm font-medium text-gray-700">项目描述</label>
              <textarea v-model="description" id="projectDescription" :disabled="props.isSaving" rows="4" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm disabled:bg-gray-100 disabled:text-gray-500"></textarea>
            </div>
          </div>
          <div class="mt-8 flex justify-end gap-3">
            <button type="button" @click="handleClose" :disabled="props.isSaving" class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-100 disabled:text-gray-400">取消</button>
            <button type="submit" :disabled="!canSubmit" class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300 disabled:cursor-not-allowed">{{ props.isSaving ? '保存中...' : '保存' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
