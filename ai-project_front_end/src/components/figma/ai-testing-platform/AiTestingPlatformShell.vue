<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, provide, reactive, ref, useSlots, watch } from 'vue'
import { useRoute } from 'vue-router'
import AiTestingHeader from '@/components/figma/ai-testing-platform/AiTestingHeader.vue'
import AiTestingSidebar from '@/components/figma/ai-testing-platform/AiTestingSidebar.vue'
import CasesPanel from '@/components/figma/ai-testing-platform/CasesPanel.vue'
import chevronDownSmall from '@/assets/figma/ai-testing-platform/chevron-down-small.svg'
import modalClose from '@/assets/figma/ai-testing-platform/modal-close.svg'
import { handleAuthExpired, isAuthExpiredResponse } from '@/lib/api/client'

const { activeAssetChild = '用例管理' } = defineProps<{
  activeAssetChild?: string
}>()

const isSidebarOpen = ref(false)
const isDesktopSidebarCollapsed = ref(false)
const route = useRoute()
const slots = useSlots()
const hasDefaultSlot = computed(() => typeof slots.default === 'function')
const projectName = ref('项目')

const isCreateRunOpen = ref(false)
const suiteFieldRef = ref<HTMLElement | null>(null)
const isSuiteMenuOpen = ref(false)

const suites = [
  '支付冒烟套件',
  '订单全量回归',
  '用户核心路径',
  '库存压力测试'
] as const

type TriggerType = '手动' | 'CI/CD' | '定时'
type EnvType = 'development' | 'production' | 'staging'

type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
}

type ProjectDetailData = {
  id: string
  name: string
}

const createRunForm = reactive({
  suiteName: '',
  environment: '' as '' | EnvType,
  trigger: '手动' as TriggerType,
  concurrency: 4,
  notifyOnFail: false
})

function openSidebar() {
  isSidebarOpen.value = true
}

function closeSidebar() {
  isSidebarOpen.value = false
}

function handleDesktopSidebarCollapseChange(collapsed: boolean) {
  isDesktopSidebarCollapsed.value = collapsed
}

function openCreateRun() {
  isCreateRunOpen.value = true
}

function closeCreateRun() {
  isCreateRunOpen.value = false
  isSuiteMenuOpen.value = false
}

function toggleSuiteMenu() {
  isSuiteMenuOpen.value = !isSuiteMenuOpen.value
}

function selectSuite(name: string) {
  createRunForm.suiteName = name
  isSuiteMenuOpen.value = false
}

function stepConcurrency(delta: number) {
  const next = Number(createRunForm.concurrency) + delta
  createRunForm.concurrency = Math.max(1, Number.isFinite(next) ? next : 1)
}

function triggerButtonClass(value: TriggerType) {
  if (createRunForm.trigger === value) {
    return 'bg-[#155DFC] border-[#155DFC] shadow-[0px_1px_2px_-1px_rgba(0,0,0,0.1),0px_1px_3px_0px_rgba(0,0,0,0.1)] text-white'
  }
  return 'bg-white border-black/10 text-[#717182]'
}

function onWindowClick(e: MouseEvent) {
  if (!isCreateRunOpen.value) return
  if (!isSuiteMenuOpen.value) return
  const target = e.target as Node | null
  if (!target) return
  const fieldEl = suiteFieldRef.value
  if (fieldEl?.contains(target)) return
  isSuiteMenuOpen.value = false
}

function submitCreateRun() {
  closeCreateRun()
}

const projectId = computed(() => {
  const id = route.params.projectId
  return typeof id === 'string' ? id.trim() : ''
})

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const resolveAuthHeader = () => {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) {
    throw new Error('登录状态已失效，请重新登录')
  }
  return `Bearer ${accessToken}`
}

const loadProjectName = async () => {
  if (!projectId.value) {
    projectName.value = '项目'
    return
  }
  try {
    const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${encodeURIComponent(projectId.value)}`, {
      method: 'GET',
      headers: {
        Authorization: resolveAuthHeader()
      }
    })
    const payload = await response.json() as ApiResponse<ProjectDetailData>
    if (isAuthExpiredResponse(response, payload)) {
      throw handleAuthExpired()
    }
    if (!response.ok || payload.code !== 0 || !payload.data?.name) {
      throw new Error(payload.message || '获取项目信息失败')
    }
    projectName.value = payload.data.name
  } catch (error) {
    if ((error as { apiCode?: number } | null)?.apiCode === 40101) return
    projectName.value = projectId.value.slice(0, 8) || '项目'
  }
}

provide('aiTestingPlatformOpenCreateRun', openCreateRun)

onMounted(() => {
  window.addEventListener('click', onWindowClick, true)
  void loadProjectName()
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick, true)
})

watch(projectId, () => {
  void loadProjectName()
})
</script>

<template>
  <div class="min-h-screen w-full bg-white">
    <div class="flex min-h-screen w-full">
      <div class="hidden shrink-0 transition-[width] duration-300 md:block" :class="isDesktopSidebarCollapsed ? 'w-[64px]' : 'w-[224px]'">
        <AiTestingSidebar
          :active-asset-child="activeAssetChild"
          :project-name="projectName"
          @collapse-change="handleDesktopSidebarCollapseChange"
        />
      </div>

      <div class="min-w-0 flex-1">
        <div class="relative w-full">
          <AiTestingHeader :project-name="projectName" @menu-click="openSidebar" />
          <slot v-if="hasDefaultSlot" />
          <CasesPanel v-else />
        </div>
      </div>
    </div>

    <div v-if="isSidebarOpen" class="fixed inset-0 z-50 md:hidden">
      <button
        class="absolute inset-0 bg-black/30"
        type="button"
        aria-label="Close sidebar"
        @click="closeSidebar"
      />
      <div class="relative h-full w-[224px] bg-white shadow-xl">
        <AiTestingSidebar :active-asset-child="activeAssetChild" :project-name="projectName" />
      </div>
    </div>

    <div v-if="isCreateRunOpen" class="fixed inset-0 z-50 flex items-center justify-center">
      <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="closeCreateRun" />

      <form
        class="relative max-h-[calc(100vh-32px)] w-full max-w-[calc(100vw-32px)] overflow-auto rounded-[16px] border border-black/10 bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:w-[512px] sm:max-w-[512px]"
        @submit.prevent="submitCreateRun"
      >
        <div class="flex h-[60.67px] items-center justify-between border-b border-black/10 px-[24px]">
          <div class="text-[16px] font-semibold leading-[24px] text-[#0A0A0A]">新建执行</div>
          <button type="button" class="h-[18px] w-[18px]" aria-label="Close" @click="closeCreateRun">
            <img :src="modalClose" alt="" class="h-full w-full" />
          </button>
        </div>

        <div class="flex flex-col gap-[16px] px-[24px] py-[20px]">
          <div ref="suiteFieldRef" class="relative flex flex-col gap-[6px]">
            <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">测试套件</div>

            <button
              type="button"
              class="relative h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] pr-[36px] text-left"
              @click="toggleSuiteMenu"
            >
              <span
                class="block truncate text-[14px] leading-[20px]"
                :class="createRunForm.suiteName ? 'text-[#0A0A0A]' : 'text-[#0A0A0A]/40'"
              >
                {{ createRunForm.suiteName || '选择测试套件' }}
              </span>
              <img :src="chevronDownSmall" alt="" class="absolute right-[12px] top-1/2 h-[13px] w-[13px] -translate-y-1/2" />
            </button>

            <div
              v-if="isSuiteMenuOpen"
              class="absolute left-0 right-0 top-[62px] z-50 overflow-hidden rounded-[10px] border border-black/10 bg-white shadow-[0px_10px_15px_-3px_rgba(0,0,0,0.1),0px_4px_6px_-4px_rgba(0,0,0,0.1)]"
            >
              <button
                v-for="name in suites"
                :key="name"
                type="button"
                class="block w-full px-[12px] py-[8px] text-left text-[14px] leading-[20px] text-[#0A0A0A] hover:bg-black/5"
                @click="selectSuite(name)"
              >
                {{ name }}
              </button>
            </div>
          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">执行环境</div>
            <div class="relative">
              <select
                v-model="createRunForm.environment"
                class="h-[36px] w-full appearance-none rounded-[10px] border border-black/10 bg-white px-[12px] pr-[36px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              >
                <option value="" disabled>选择环境</option>
                <option value="development">development</option>
                <option value="production">production</option>
                <option value="staging">staging</option>
              </select>
              <img :src="chevronDownSmall" alt="" class="pointer-events-none absolute right-[12px] top-1/2 h-[13px] w-[13px] -translate-y-1/2" />
            </div>
          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">触发方式</div>
            <div class="flex flex-wrap gap-[8px]">
              <button
                type="button"
                class="h-[32px] rounded-[10px] border px-[12px] text-[14px] font-medium leading-[20px]"
                :class="triggerButtonClass('手动')"
                @click="createRunForm.trigger = '手动'"
              >
                手动
              </button>
              <button
                type="button"
                class="h-[32px] rounded-[10px] border px-[12px] text-[14px] font-medium leading-[20px]"
                :class="triggerButtonClass('CI/CD')"
                @click="createRunForm.trigger = 'CI/CD'"
              >
                CI/CD
              </button>
              <button
                type="button"
                class="h-[32px] rounded-[10px] border px-[12px] text-[14px] font-medium leading-[20px]"
                :class="triggerButtonClass('定时')"
                @click="createRunForm.trigger = '定时'"
              >
                定时
              </button>
            </div>
          </div>

          <div class="flex flex-col gap-[6px]">
            <div class="text-[14px] font-medium leading-[20px] text-[#0A0A0A]">并发数</div>
            <div class="relative h-[36px] w-full overflow-hidden rounded-[10px] border border-black/10 bg-white">
              <input
                v-model.number="createRunForm.concurrency"
                type="number"
                inputmode="numeric"
                class="h-full w-full bg-transparent pl-[12px] pr-[44px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
                min="1"
              />
              <div class="absolute right-0 top-0 flex h-full w-[36px] flex-col border-l border-black/10">
                <button
                  type="button"
                  class="flex h-1/2 w-full items-center justify-center"
                  aria-label="Increase concurrency"
                  @click="stepConcurrency(1)"
                >
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 2L9 6H1L5 2Z" fill="#717182" />
                  </svg>
                </button>
                <button
                  type="button"
                  class="flex h-1/2 w-full items-center justify-center border-t border-black/10"
                  aria-label="Decrease concurrency"
                  @click="stepConcurrency(-1)"
                >
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 8L1 4H9L5 8Z" fill="#717182" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <label class="flex items-center gap-[8px]">
            <input
              v-model="createRunForm.notifyOnFail"
              type="checkbox"
              class="h-[16px] w-[16px] rounded-[4px] border border-black/10 text-[#155DFC] accent-[#155DFC]"
            />
            <span class="text-[14px] leading-[20px] text-[#0A0A0A]">失败时推送通知</span>
          </label>
        </div>

        <div class="flex gap-[8px] px-[24px] pb-[24px]">
          <button
            type="button"
            class="h-[36px] flex-1 rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#0A0A0A]"
            @click="closeCreateRun"
          >
            取消
          </button>
          <button
            type="submit"
            class="h-[36px] flex-1 rounded-[10px] bg-[#155DFC] text-[14px] font-medium leading-[20px] text-white"
          >
            开始执行
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
