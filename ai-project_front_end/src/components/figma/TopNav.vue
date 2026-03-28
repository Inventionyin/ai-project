<script setup lang="ts">
import { Bell, ChevronDown, Menu, Plus, Search } from 'lucide-vue-next'
import { onBeforeUnmount, onMounted, ref } from 'vue'

const projects = ['支付服务', '用户中心', '订单系统', '库存管理']
const selectedProject = ref(projects[0])
const isProjectMenuOpen = ref(false)
const projectMenuRef = ref<HTMLElement | null>(null)

const selectProject = (name: string) => {
  selectedProject.value = name
  localStorage.setItem('selectedProject', name)
  isProjectMenuOpen.value = false
}

const onWindowClick = (e: MouseEvent) => {
  const el = projectMenuRef.value
  if (!el) return
  if (!el.contains(e.target as Node)) {
    isProjectMenuOpen.value = false
  }
}

onMounted(() => {
  const saved = localStorage.getItem('selectedProject')
  if (saved && projects.includes(saved)) {
    selectedProject.value = saved
  }
  window.addEventListener('click', onWindowClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick)
})
</script>

<template>
  <header class="w-full bg-white border-b-[0.6667px] border-black/10">
    <div class="mx-auto w-full max-w-[715.33px] min-h-12 px-4 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <button class="w-[26px] h-[26px] rounded flex items-center justify-center">
          <Menu class="w-[18px] h-[18px] text-[#717182]" />
        </button>

        <div ref="projectMenuRef" class="relative flex items-center gap-1">
          <button
            class="h-6 text-base font-medium text-[#717182] leading-6"
            type="button"
            @click.stop="isProjectMenuOpen = !isProjectMenuOpen"
          >
            项目
          </button>
          <button type="button" class="flex items-center gap-1" @click.stop="isProjectMenuOpen = !isProjectMenuOpen">
            <ChevronDown
              class="w-[14px] h-[14px] text-[#717182] transition-transform"
              :class="isProjectMenuOpen ? 'rotate-180' : ''"
            />
            <div class="h-5 text-sm font-normal text-[#0A0A0A] leading-5">{{ selectedProject }}</div>
          </button>

          <div
            v-if="isProjectMenuOpen"
            class="absolute left-0 top-full mt-2 w-[180px] rounded-[10px] border-[0.6667px] border-black/10 bg-white shadow-lg overflow-hidden z-20"
          >
            <button
              v-for="name in projects"
              :key="name"
              type="button"
              class="w-full h-9 px-3 flex items-center text-sm leading-5 transition-colors"
              :class="name === selectedProject ? 'bg-[rgba(43,127,255,0.12)] text-brand-blue' : 'text-[#0A0A0A] hover:bg-[#ECECF0]'"
              @click="selectProject(name)"
            >
              {{ name }}
            </button>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div class="relative w-full sm:w-[224px]">
          <Search class="absolute left-[10px] top-1/2 -translate-y-1/2 w-[15px] h-[15px] text-[#717182]" />
          <input
            class="w-full h-8 pl-8 pr-3 rounded-[10px] bg-[#ECECF0] text-sm text-[#0A0A0A] placeholder:text-[#0A0A0A] outline-none"
            placeholder="搜索用例、运行记录..."
            type="text"
          />
        </div>

        <button class="w-[100px] h-8 rounded-[10px] bg-brand-blue text-white flex items-center justify-center gap-1.5">
          <Plus class="w-[14px] h-[14px]" />
          <span class="text-sm font-medium leading-5">新建执行</span>
        </button>

        <button class="relative w-[29px] h-[29px] rounded flex items-center justify-center">
          <Bell class="w-[17px] h-[17px] text-[#717182]" />
          <span class="absolute right-[2px] top-[2px] w-2 h-2 rounded-full bg-[#FB2C36]"></span>
        </button>

        <div class="w-7 h-7 rounded-full bg-brand-blue flex items-center justify-center">
          <span class="text-xs font-semibold text-white leading-4">ZS</span>
        </div>
      </div>
    </div>
  </header>
</template>
