<script setup lang="ts">
import { computed, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UserProfile from '@/components/UserProfile.vue'
import headerMenu from '@/assets/figma/ai-testing-platform/header-menu.svg'
import headerProjectChevron from '@/assets/figma/ai-testing-platform/header-project-chevron.svg'
import headerPlus from '@/assets/figma/ai-testing-platform/header-plus.svg'
import headerSearch from '@/assets/figma/ai-testing-platform/header-search.svg'
import headerBell from '@/assets/figma/ai-testing-platform/header-bell.svg'

defineEmits<{
  (e: 'menu-click'): void
}>()

const { projectName = '项目' } = defineProps<{
  projectName?: string
}>()

const router = useRouter()
const route = useRoute()
const openCreateRun = inject<() => void>('aiTestingPlatformOpenCreateRun', () => {})
const projectId = computed(() => String(route.params.projectId || '1'))

function goHome() {
  router.push('/projects')
}

function openNotifications() {
  router.push(`/projects/${encodeURIComponent(projectId.value)}/settings/ops-health`)
}
</script>

<template>
  <header class="w-full border-b border-black/10 bg-white md:relative md:h-[48px]">
    <div class="flex flex-wrap items-center gap-[8px] px-[16px] py-[8px] md:hidden">
      <button class="h-[26px] w-[26px] rounded-[4px] p-[4px]" type="button" aria-label="Open sidebar" @click="$emit('menu-click')">
        <img :src="headerMenu" alt="" class="h-full w-full" />
      </button>

      <div class="flex min-w-[160px] flex-1 items-center gap-[4px]">
        <button class="h-[24px] w-[32px] text-center text-[16px] font-medium leading-[24px] text-[#717182]" type="button" @click="goHome">
          项目
        </button>
        <img :src="headerProjectChevron" alt="" class="h-[14px] w-[14px]" />
        <div class="text-left text-[14px] leading-[20px] text-[#0A0A0A]">{{ projectName }}</div>
      </div>

      <div class="flex w-full items-center gap-[8px]">
        <div class="relative h-[32px] flex-1 rounded-[10px] bg-[#ECECF0]">
          <img :src="headerSearch" alt="" class="absolute left-[10px] top-[8.5px] h-[15px] w-[15px]" />
          <div class="absolute left-[32px] top-1/2 -translate-y-1/2 text-[14px] leading-[20px] text-[#0A0A0A]">
            搜索用例、运行记录...
          </div>
        </div>

        <button class="relative h-[32px] w-[100px] shrink-0 rounded-[10px] bg-[#155DFC]" type="button" @click="openCreateRun">
          <img :src="headerPlus" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
          <span class="absolute left-[32px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
            新建执行
          </span>
        </button>

        <button class="relative h-[29px] w-[29px] shrink-0 rounded-[4px] hover:bg-[#F5F5F5]" type="button" aria-label="打开通知与告警" @click="openNotifications">
          <img :src="headerBell" alt="" class="absolute left-[6px] top-[6px] h-[17px] w-[17px]" />
          <span class="absolute left-[19px] top-[2px] h-[8px] w-[8px] rounded-full bg-[#FB2C36]" />
        </button>

        <UserProfile />
      </div>
    </div>

    <div class="hidden md:flex h-[48px] items-center justify-between gap-[12px] px-[16px]">
      <div class="flex min-w-0 items-center gap-[12px]">
        <button class="h-[26px] w-[26px] rounded-[4px] p-[4px]" type="button" aria-label="Open sidebar" @click="$emit('menu-click')">
          <img :src="headerMenu" alt="" class="h-full w-full" />
        </button>

        <div class="flex h-[24px] items-center gap-[4px]">
          <button class="h-[24px] w-[32px] text-center text-[16px] font-medium leading-[24px] text-[#717182]" type="button" @click="goHome">
            项目
          </button>
          <img :src="headerProjectChevron" alt="" class="h-[14px] w-[14px]" />
          <div class="text-left text-[14px] leading-[20px] text-[#0A0A0A]">{{ projectName }}</div>
        </div>
      </div>

      <div class="flex items-center gap-[12px]">
        <div class="relative h-[32px] w-[224px] rounded-[10px] bg-[#ECECF0]">
          <img :src="headerSearch" alt="" class="absolute left-[10px] top-[8.5px] h-[15px] w-[15px]" />
          <div class="absolute left-[32px] top-1/2 -translate-y-1/2 text-[14px] leading-[20px] text-[#0A0A0A]">
            搜索用例、运行记录...
          </div>
        </div>

        <button class="relative h-[32px] w-[100px] rounded-[10px] bg-[#155DFC]" type="button" @click="openCreateRun">
          <img :src="headerPlus" alt="" class="absolute left-[12px] top-[9px] h-[14px] w-[14px]" />
          <span class="absolute left-[32px] top-[6.33px] text-[14px] font-medium leading-[20px] text-white">
            新建执行
          </span>
        </button>

        <button class="relative h-[29px] w-[29px] rounded-[4px] hover:bg-[#F5F5F5]" type="button" aria-label="打开通知与告警" @click="openNotifications">
          <img :src="headerBell" alt="" class="absolute left-[6px] top-[6px] h-[17px] w-[17px]" />
          <span class="absolute left-[19px] top-[2px] h-[8px] w-[8px] rounded-full bg-[#FB2C36]" />
        </button>

        <UserProfile />
      </div>
    </div>
  </header>
</template>
