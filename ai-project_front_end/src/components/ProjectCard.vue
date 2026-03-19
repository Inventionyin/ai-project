<script setup lang="ts">
interface ProjectStats {
  value: string | number
  label: string
  color: string
}

interface ProjectData {
  id: string
  title: string
  description: string
  tags: { text: string; bg: string; color: string }[]
  stats: ProjectStats[]
  iconColor: string
  owner: string
  ownerId: string
  date: string
}

defineProps<{
  project: ProjectData
}>()

const emit = defineEmits<{
  (e: 'edit', project: ProjectData): void
  (e: 'delete', project: ProjectData): void
}>()
</script>

<template>
  <div class="relative group bg-white border border-gray-100 rounded-[14px] p-5 shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col gap-5 h-full">
    <!-- Action Buttons -->
    <div class="absolute top-4 right-4 z-10 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
      <button @click.stop="emit('edit', project)" class="w-7 h-7 rounded-full bg-gray-100 hover:bg-blue-100 text-gray-600 hover:text-blue-600 flex items-center justify-center transition-colors" title="编辑项目">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.5L15.232 5.232z" />
        </svg>
      </button>
      <button @click.stop="emit('delete', project)" class="w-7 h-7 rounded-full bg-gray-100 hover:bg-red-100 text-gray-600 hover:text-red-600 flex items-center justify-center transition-colors" title="删除项目">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>

    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div class="flex items-start gap-3 flex-1 min-w-0">
        <!-- Project Icon -->
        <div 
          class="w-10 h-10 rounded-[10px] flex items-center justify-center text-white font-bold text-lg shrink-0"
          :class="project.iconColor || 'bg-indigo-600'"
        >
          {{ project.title.substring(0, 1) }}
        </div>
        
        <div class="flex flex-col min-w-0">
          <h3 class="text-base font-bold text-gray-900 leading-tight truncate">{{ project.title }}</h3>
          <p class="text-xs text-gray-500 mt-1 line-clamp-1">{{ project.description }}</p>
        </div>
      </div>


    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-3 gap-2 border-t border-gray-50 pt-4">
      <div 
        v-for="(stat, idx) in project.stats" 
        :key="idx"
        class="flex flex-col"
      >
        <span 
          class="text-lg font-bold leading-tight"
          :class="stat.color || 'text-gray-900'"
        >
          {{ stat.value }}
        </span>
        <span class="text-xs text-gray-400 mt-0.5">{{ stat.label }}</span>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between pt-4 border-t border-gray-50 text-xs text-gray-400">
      <div class="flex items-center gap-1.5">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
        <span>Owner: {{ project.owner }}</span>
      </div>
      <div class="flex items-center gap-1.5">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{{ project.date }}</span>
      </div>
    </div>

    <!-- Action Button -->
    <button class="w-full mt-auto bg-indigo-50 hover:bg-indigo-100 text-indigo-600 font-medium py-2 rounded-[8px] text-xs transition-colors">
      进入项目
    </button>
  </div>
</template>
