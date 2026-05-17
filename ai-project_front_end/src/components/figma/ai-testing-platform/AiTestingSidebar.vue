<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import sidebarLogo from '@/assets/figma/ai-testing-platform/sidebar-logo.svg'
import projectIcon from '@/assets/figma/ai-testing-platform/project-icon.svg'
import chevronDownSmall from '@/assets/figma/ai-testing-platform/chevron-down-small.svg'
import navDashboard from '@/assets/figma/ai-testing-platform/nav-dashboard.svg'
import navAsset from '@/assets/figma/ai-testing-platform/nav-asset.svg'
import navChevron from '@/assets/figma/ai-testing-platform/nav-chevron.svg'
import navCases from '@/assets/figma/ai-testing-platform/nav-cases.svg'
import navSuite from '@/assets/figma/ai-testing-platform/nav-suite.svg'
import navApiCollection from '@/assets/figma/ai-testing-platform/nav-api-collection.svg'
import navTestData from '@/assets/figma/ai-testing-platform/nav-test-data.svg'
import navExecution from '@/assets/figma/ai-testing-platform/nav-execution.svg'
import navChevron2 from '@/assets/figma/ai-testing-platform/nav-chevron-2.svg'
import navRunHistory from '@/assets/figma/ai-testing-platform/nav-run-history.svg'
import navWorker from '@/assets/figma/ai-testing-platform/nav-worker.svg'
import navReports from '@/assets/figma/ai-testing-platform/nav-reports.svg'
import navAiAssistant from '@/assets/figma/ai-testing-platform/nav-ai-assistant.svg'
import navAudit from '@/assets/figma/ai-testing-platform/nav-audit.svg'
import navEnv from '@/assets/figma/ai-testing-platform/nav-env.svg'
import navMember from '@/assets/figma/ai-testing-platform/nav-member.svg'
import navIntegrations from '@/assets/figma/ai-testing-platform/nav-integrations.svg'

type LinkItem = {
  label: string
  icon: string
  to?: string
}

type GroupItem = {
  label: string
  icon: string
  chevron: string
  children: LinkItem[]
}

const { activeAssetChild, projectName = '项目' } = defineProps<{
  activeAssetChild?: string
  projectName?: string
}>()

const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)

function navigateTo(item: LinkItem) {
  if (!item.to) return
  router.push(item.to)
}

const projectId = computed(() => {
  const id = route.params.projectId
  return typeof id === 'string' && id.length > 0 ? id : '1'
})

const resolvedActiveAssetChild = computed(() => {
  if (typeof activeAssetChild === 'string') return activeAssetChild
  if (route.path.startsWith(`/projects/${projectId.value}/assets/suites`)) return '测试套件'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/testcases`)) return '用例管理'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/apis`)) return '接口集合'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/data`)) return '测试数据'
  if (route.path.startsWith(`/projects/${projectId.value}/runs`)) return '运行记录'
  if (route.path.startsWith(`/projects/${projectId.value}/workers`)) return 'Worker 管理'
  if (route.path.startsWith(`/projects/${projectId.value}/ai-assistant`)) return 'AI 助手'
  if (route.path.startsWith(`/projects/${projectId.value}/requirements/docs`)) return '需求文档中心'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/platform-records`)) return '平台记录'
  if (route.path.startsWith('/figma/untitled-47-1415')) return '测试套件'
  if (route.path.startsWith('/figma/untitled-34-158')) return '用例管理'
  if (route.path.startsWith('/figma/untitled-9-3')) return '用例管理'
  if (route.path.startsWith('/figma/untitled-88-3')) return '接口集合'
  if (route.path.startsWith('/figma/untitled-97-879')) return '测试数据'
  if (route.path.startsWith('/figma/untitled-140-6408')) return '运行记录'
  return ''
})

function isAssetChildActive(label: string) {
  return resolvedActiveAssetChild.value === label
}

function isMainLinkActive(item: LinkItem) {
  if (!item.to) return false
  return route.path.startsWith(item.to)
}

function isExtraLinkActive(item: LinkItem) {
  if (!item.to) return false
  return route.path === item.to || route.path.startsWith(`${item.to}/`)
}

const mainLinks = computed<LinkItem[]>(() => [
  { label: '仪表盘', icon: navDashboard, to: `/projects/${projectId.value}/dashboard` }
])

const groups = computed<GroupItem[]>(() => [
  {
    label: '资产中心',
    icon: navAsset,
    chevron: navChevron,
    children: [
      { label: '用例管理', icon: navCases, to: `/projects/${projectId.value}/assets/testcases` },
      { label: '测试套件', icon: navSuite, to: `/projects/${projectId.value}/assets/suites` },
      { label: '接口集合', icon: navApiCollection, to: `/projects/${projectId.value}/assets/apis` },
      { label: '测试数据', icon: navTestData, to: `/projects/${projectId.value}/assets/data` }
    ]
  },
  {
    label: '执行中心',
    icon: navExecution,
    chevron: navChevron2,
    children: [
      { label: '运行记录', icon: navRunHistory, to: `/projects/${projectId.value}/runs` },
      { label: 'Worker 管理', icon: navWorker, to: `/projects/${projectId.value}/workers` }
    ]
  }
])

const extraLinks = computed<LinkItem[]>(() => [
  { label: '报告中心', icon: navReports, to: `/projects/${projectId.value}/reports` },
  { label: 'Allure报告', icon: navReports, to: `/projects/${projectId.value}/reports/allure` },
  { label: '需求文档中心', icon: navAudit, to: `/projects/${projectId.value}/requirements/docs` },
  { label: 'AI 助手', icon: navAiAssistant, to: `/projects/${projectId.value}/ai-assistant` }
])

const settingsLinks = computed<LinkItem[]>(() => [
  { label: '平台记录', icon: navAudit, to: `/projects/${projectId.value}/settings/platform-records` },
  { label: '环境管理', icon: navEnv, to: `/projects/${projectId.value}/settings/environments` },
  { label: '成员权限', icon: navMember, to: '/settings/rbac' },
  { label: '集成配置', icon: navIntegrations, to: '/settings/integrations' },
  { label: '审计日志', icon: navAudit, to: '/settings/audit' }
])
</script>

<template>
  <aside class="flex h-full min-h-screen w-full flex-col bg-[#FAFAFA] border-r border-[#E5E5E5] transition-all duration-300 ease-in-out">
    <div class="flex h-[66.17px] items-center gap-[10px] border-b border-[#E5E5E5] pl-[16px]" :class="isCollapsed ? 'justify-center pl-0' : ''">
      <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px] bg-[#155DFC] flex-shrink-0">
        <img :src="sidebarLogo" alt="" class="h-[15px] w-[15px]" />
      </div>

      <div v-if="!isCollapsed" class="flex flex-col">
        <div class="text-[14px] font-semibold leading-[1.25] text-[#0A0A0A]">WeiTesting</div>
        <div class="text-[12px] leading-[16px] text-[rgba(10,10,10,0.5)]">v1.0.0</div>
      </div>
    </div>

    <div class="h-[48.67px] border-b border-[#E5E5E5] px-[12px] pt-[8px] pb-[0.67px]">
      <button
        type="button"
        class="flex h-[32px] w-full items-center gap-[8px] rounded-[10px] bg-[#F5F5F5] px-[8px]"
        :class="isCollapsed ? 'justify-center' : ''"
      >
        <span class="flex h-[20px] w-[20px] items-center justify-center rounded-[4px] bg-[#DBEAFE] flex-shrink-0">
          <img :src="projectIcon" alt="" class="h-[12px] w-[12px]" />
        </span>
        <span v-if="!isCollapsed" class="flex-1 text-left text-[14px] leading-[20px] font-medium text-[#0A0A0A]">{{ projectName }}</span>
        <img v-if="!isCollapsed" :src="chevronDownSmall" alt="" class="h-[13px] w-[13px]" />
      </button>
    </div>

    <nav class="flex-1 overflow-y-auto overflow-x-hidden pb-[12px]">
      <div class="px-[8px] pt-[8px]">
        <button
          v-for="item in mainLinks"
          :key="item.label"
          type="button"
          class="flex h-[36px] w-full items-center gap-[8px] rounded-[10px] pl-[12px]"
          :class="[isMainLinkActive(item) ? 'bg-[#155DFC]' : '', isCollapsed ? 'justify-center pl-0' : '']"
          @click="navigateTo(item)"
        >
          <img :src="item.icon" alt="" class="h-[16px] w-[16px] flex-shrink-0" :class="isMainLinkActive(item) ? 'filter brightness-0 invert' : ''" />
          <span
            v-if="!isCollapsed"
            class="text-[14px] leading-[20px]"
            :class="isMainLinkActive(item) ? 'text-white' : 'text-[rgba(10,10,10,0.7)]'"
          >
            {{ item.label }}
          </span>
        </button>
      </div>

      <div v-for="group in groups" :key="group.label" class="px-[8px] pt-[2px]">
        <div class="flex w-full flex-col">
          <button type="button" class="flex h-[36px] items-center gap-[8px] rounded-[10px] px-[12px]" :class="isCollapsed ? 'justify-center px-0' : ''">
            <img :src="group.icon" alt="" class="h-[16px] w-[16px] flex-shrink-0" />
            <span v-if="!isCollapsed" class="flex-1 text-left text-[14px] leading-[20px] font-medium text-[rgba(10,10,10,0.7)]">
              {{ group.label }}
            </span>
            <img v-if="!isCollapsed" :src="group.chevron" alt="" class="h-[14px] w-[14px]" />
          </button>

          <div v-if="!isCollapsed" class="ml-[16px] mt-[4px] flex w-[174.67px] flex-col gap-[2px]">
            <button
              v-for="child in group.children"
              :key="child.label"
              type="button"
              class="flex h-[36px] w-full items-center gap-[8px] rounded-[10px] pl-[12px]"
              :class="isAssetChildActive(child.label) ? 'bg-[#155DFC]' : ''"
              @click="navigateTo(child)"
            >
              <img :src="child.icon" alt="" class="h-[15px] w-[15px] flex-shrink-0" :class="isAssetChildActive(child.label) ? 'filter brightness-0 invert' : ''" />
              <span
                class="text-[14px] leading-[20px]"
                :class="isAssetChildActive(child.label) ? 'text-white' : 'text-[rgba(10,10,10,0.7)]'"
              >
                {{ child.label }}
              </span>
            </button>
          </div>
        </div>
      </div>

      <div class="px-[8px] pt-[8px]">
        <button
          v-for="item in extraLinks"
          :key="item.label"
          type="button"
          class="flex h-[36px] w-full items-center gap-[8px] rounded-[10px] pl-[12px]"
          :class="[isExtraLinkActive(item) ? 'bg-[#155DFC]' : '', isCollapsed ? 'justify-center pl-0' : '']"
          @click="navigateTo(item)"
        >
          <img :src="item.icon" alt="" class="h-[16px] w-[16px] flex-shrink-0" :class="isExtraLinkActive(item) ? 'filter brightness-0 invert' : ''" />
          <span
            v-if="!isCollapsed"
            class="text-[14px] font-medium leading-[20px]"
            :class="isExtraLinkActive(item) ? 'text-white' : 'text-[rgba(10,10,10,0.7)]'"
          >
            {{ item.label }}
          </span>
        </button>
      </div>

      <div class="mx-[8px] mt-[10px] border-t border-[#E5E5E5] pt-[10px]">
        <div v-if="!isCollapsed" class="pl-[12px] text-[12px] leading-[16px] text-[rgba(10,10,10,0.4)]">设置</div>
        <div class="mt-[6px] flex flex-col gap-[2px]">
          <button
            v-for="item in settingsLinks"
            :key="item.label"
            type="button"
            class="flex h-[36px] w-full items-center gap-[8px] rounded-[10px] pl-[12px]"
            :class="[isExtraLinkActive(item) ? 'bg-[#155DFC]' : '', isCollapsed ? 'justify-center pl-0' : '']"
            @click="navigateTo(item)"
          >
            <img :src="item.icon" alt="" class="h-[16px] w-[16px] flex-shrink-0" :class="isExtraLinkActive(item) ? 'filter brightness-0 invert' : ''" />
            <span v-if="!isCollapsed" class="text-[14px] leading-[20px]" :class="isExtraLinkActive(item) ? 'text-white' : 'text-[rgba(10,10,10,0.7)]'">
              {{ item.label }}
            </span>
          </button>
        </div>
      </div>
    </nav>

  </aside>
</template>
