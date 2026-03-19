<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AiTestingSidebar from '@/components/figma/ai-testing-platform/AiTestingSidebar.vue'
import { Search, Plus, Bell, ChevronRight, Home, ChevronDown, Menu } from 'lucide-vue-next'

const projects = ['支付服务', '用户中心', '订单系统', '库存管理']
const selectedProject = ref(localStorage.getItem('selectedProject') ?? projects[0])

const isProjectMenuOpen = ref(false)
const projectMenuRef = ref<HTMLElement | null>(null)
const isSidebarOpen = ref(false)

const selectProject = (name: string) => {
  selectedProject.value = name
  localStorage.setItem('selectedProject', name)
  isProjectMenuOpen.value = false
}

const openSidebar = () => {
  isSidebarOpen.value = true
}

const closeSidebar = () => {
  isSidebarOpen.value = false
}

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

const onWindowClick = (e: MouseEvent) => {
  const el = projectMenuRef.value
  if (!el) return
  if (!el.contains(e.target as Node)) {
    isProjectMenuOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('click', onWindowClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick)
})
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <div class="hidden w-[224px] shrink-0 md:block">
      <AiTestingSidebar />
    </div>
    
    <div class="flex flex-1 flex-col overflow-hidden">
      <header class="bg-white shadow-sm z-10 border-b border-gray-200">
        <div class="max-w-7xl mx-auto py-3 px-4 sm:px-6 lg:px-8 flex flex-wrap justify-between items-center gap-4">
             <!-- Left: Breadcrumb / Project Context -->
             <div class="flex items-center gap-2 text-sm text-gray-500">
                <button class="md:hidden p-2 -ml-2 rounded-md hover:bg-gray-100" type="button" aria-label="Open sidebar" @click="openSidebar">
                  <Menu class="w-5 h-5 text-gray-500" />
                </button>
                <button class="hidden md:block p-2 -ml-2 rounded-md hover:bg-gray-100" type="button" aria-label="Toggle sidebar" @click="toggleSidebar">
                  <Menu class="w-5 h-5 text-gray-500" />
                </button>
                <div class="p-1.5 bg-gray-100 rounded-md">
                   <Home class="w-4 h-4 text-gray-500" />
                </div>
                <span class="text-xs">项目</span>
                <ChevronRight class="w-4 h-4 text-gray-400" />
                <div ref="projectMenuRef" class="relative">
                  <button
                    class="font-medium bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs flex items-center gap-1"
                    @click.stop="isProjectMenuOpen = !isProjectMenuOpen"
                    type="button"
                  >
                    <span>{{ selectedProject }}</span>
                    <ChevronDown class="w-4 h-4" :class="isProjectMenuOpen ? 'rotate-180' : ''" />
                  </button>
                  <div
                    v-if="isProjectMenuOpen"
                    class="absolute left-0 mt-2 w-44 rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden z-20"
                  >
                    <button
                      v-for="name in projects"
                      :key="name"
                      type="button"
                      class="w-full px-3 py-2 text-left text-sm transition-colors"
                      :class="name === selectedProject ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'"
                      @click="selectProject(name)"
                    >
                      {{ name }}
                    </button>
                  </div>
                </div>
             </div>

             <!-- Right: Actions & Profile -->
             <div class="flex flex-wrap items-center gap-4">
                <!-- Search -->
                <div class="relative hidden md:block">
                   <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                   <input 
                      type="text" 
                      placeholder="搜索用例、运行记录..." 
                      class="pl-9 pr-4 py-1.5 bg-gray-100 border-none rounded-lg text-sm focus:ring-2 focus:ring-blue-500 w-64"
                   />
                </div>

                <!-- New Execution Button -->
                <button class="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition-colors">
                   <Plus class="w-4 h-4" />
                   <span>新建执行</span>
                </button>

                <div class="h-6 w-px bg-gray-200 mx-1"></div>

                <!-- Notifications -->
                <button class="p-2 text-gray-400 hover:text-gray-600 relative">
                    <Bell class="w-5 h-5" />
                    <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
                </button>
                
                <!-- Avatar -->
                <div class="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-xs font-bold ring-2 ring-white shadow-sm">
                   ZS
                </div>
             </div>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto bg-gray-50 p-6">
        <router-view />
      </main>
    </div>

    <div v-if="isSidebarOpen" class="fixed inset-0 z-50 md:hidden">
      <button class="absolute inset-0 bg-black/30" type="button" aria-label="Close sidebar" @click="closeSidebar" />
      <div class="relative h-full w-[224px] bg-white shadow-xl">
        <AiTestingSidebar />
      </div>
    </div>
  </div>
</template>
