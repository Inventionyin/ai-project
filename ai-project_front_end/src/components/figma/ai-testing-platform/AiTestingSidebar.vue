<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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
import navExecution from '@/assets/figma/ai-testing-platform/nav-execution.svg'
import navChevron2 from '@/assets/figma/ai-testing-platform/nav-chevron-2.svg'
import navRunHistory from '@/assets/figma/ai-testing-platform/nav-run-history.svg'
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

const emit = defineEmits<{
  'collapse-change': [collapsed: boolean]
}>()

const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const activeExpandedGroup = ref('')

function navigateTo(item: LinkItem) {
  if (!item.to) return
  router.push(item.to)
}

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
  emit('collapse-change', isCollapsed.value)
}

function toggleGroup(label: string) {
  if (isCollapsed.value) return
  activeExpandedGroup.value = activeExpandedGroup.value === label ? '' : label
}

function isGroupExpanded(label: string) {
  return !isCollapsed.value && activeExpandedGroup.value === label
}

function toggleSettings() {
  if (isCollapsed.value) return
  activeExpandedGroup.value = activeExpandedGroup.value === '设置' ? '' : '设置'
}

function openProjectSwitcher() {
  router.push('/projects')
}

const projectId = computed(() => {
  const id = route.params.projectId
  return typeof id === 'string' && id.length > 0 ? id : '1'
})

const resolvedActiveAssetChild = computed(() => {
  if (typeof activeAssetChild === 'string') return activeAssetChild
  if (route.path.startsWith(`/projects/${projectId.value}/trial-operation`)) return '试运行看板'
  if (route.path === `/projects/${projectId.value}/assets`) return '资产中心'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/suites`)) return '测试套件'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/testcases`)) return '用例管理'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/apis`)) return '接口管理'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/data`)) return '测试数据'
  if (route.path === `/projects/${projectId.value}/ai`) return 'AI能力'
  if (route.path.startsWith(`/projects/${projectId.value}/ai/generate-cases`)) return '自动生成测试用例'
  if (route.path.startsWith(`/projects/${projectId.value}/ai/requirements`)) return '需求解析'
  if (route.path.startsWith(`/projects/${projectId.value}/ai/case-governance`)) return '用例治理'
  if (route.path.startsWith(`/projects/${projectId.value}/ai/change-impact`)) return '变更影响分析'
  if (route.path.startsWith(`/projects/${projectId.value}/automation/ui`)) return 'UI自动化'
  if (route.path.startsWith(`/projects/${projectId.value}/automation/api`)) return '接口自动化'
  if (route.path.startsWith(`/projects/${projectId.value}/automation/performance`)) return '性能自动化'
  if (route.path === `/projects/${projectId.value}/automation`) return '自动化执行'
  if (route.path.startsWith(`/projects/${projectId.value}/runs`)) return '运行记录'
  if (route.path.startsWith(`/projects/${projectId.value}/workers`)) return '执行资源'
  if (route.path.startsWith(`/projects/${projectId.value}/ai-assistant`)) return '自动生成测试用例'
  if (route.path.startsWith(`/projects/${projectId.value}/requirements/docs`)) return '需求管理'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/platform-records`)) return '平台记录'
  if (route.path === `/projects/${projectId.value}/settings`) return '设置'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/integrations`)) return '集成配置'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/doc-parse-jobs`)) return '文档解析任务'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/devops`)) return '平台配置'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/executors`)) return '平台配置'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/plugins`)) return '插件市场'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/security-audit`)) return '安全审计'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/ci-token-governance`)) return 'CI Token 治理'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/ai-capabilities`)) return '平台配置'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/ops-health`)) return '运维健康'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/acceptance`)) return '验收中心'
  if (route.path.startsWith('/figma/untitled-47-1415')) return '测试套件'
  if (route.path.startsWith('/figma/untitled-34-158')) return '用例管理'
  if (route.path.startsWith('/figma/untitled-9-3')) return '用例管理'
  if (route.path.startsWith('/figma/untitled-88-3')) return '接口管理'
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
      { label: '资产总览', icon: navAsset, to: `/projects/${projectId.value}/assets` },
      { label: '需求管理', icon: navAudit, to: `/projects/${projectId.value}/requirements/docs` },
      { label: '用例管理', icon: navCases, to: `/projects/${projectId.value}/assets/testcases` },
      { label: '接口管理', icon: navApiCollection, to: `/projects/${projectId.value}/assets/apis` },
      { label: '测试套件', icon: navSuite, to: `/projects/${projectId.value}/assets/suites` }
    ]
  },
  {
    label: 'AI能力',
    icon: navAiAssistant,
    chevron: navChevron2,
    children: [
      { label: 'AI总览', icon: navAiAssistant, to: `/projects/${projectId.value}/ai` },
      { label: '自动生成测试用例', icon: navAiAssistant, to: `/projects/${projectId.value}/ai/generate-cases` },
      { label: '需求解析', icon: navAudit, to: `/projects/${projectId.value}/ai/requirements` },
      { label: '用例治理', icon: navCases, to: `/projects/${projectId.value}/ai/case-governance` },
      { label: '变更影响分析', icon: navAudit, to: `/projects/${projectId.value}/ai/change-impact` }
    ]
  },
  {
    label: '自动化执行',
    icon: navExecution,
    chevron: navChevron2,
    children: [
      { label: '执行总览', icon: navExecution, to: `/projects/${projectId.value}/automation` },
      { label: 'UI自动化', icon: navCases, to: `/projects/${projectId.value}/automation/ui` },
      { label: '接口自动化', icon: navApiCollection, to: `/projects/${projectId.value}/automation/api` },
      { label: '性能自动化', icon: navReports, to: `/projects/${projectId.value}/automation/performance` },
      { label: '运行记录', icon: navRunHistory, to: `/projects/${projectId.value}/runs` },
      { label: '报告中心', icon: navReports, to: `/projects/${projectId.value}/reports` }
    ]
  }
])

const settingsLinks = computed<LinkItem[]>(() => [
  { label: '设置总览', icon: navIntegrations, to: `/projects/${projectId.value}/settings` },
  { label: '权限', icon: navMember, to: '/settings/rbac' },
  { label: '环境管理', icon: navEnv, to: `/projects/${projectId.value}/settings/environments` },
  { label: '集成配置', icon: navIntegrations, to: `/projects/${projectId.value}/settings/integrations` },
  { label: 'API Token / CI Token', icon: navIntegrations, to: `/projects/${projectId.value}/settings/ci-token-governance` },
  { label: '平台配置', icon: navEnv, to: `/projects/${projectId.value}/settings/platform-records` },
  { label: '插件市场', icon: navAsset, to: `/projects/${projectId.value}/settings/plugins` },
  { label: '安全审计', icon: navAudit, to: `/projects/${projectId.value}/settings/security-audit` },
  { label: '运维健康', icon: navAudit, to: `/projects/${projectId.value}/settings/ops-health` },
  { label: '验收中心', icon: navAudit, to: `/projects/${projectId.value}/settings/acceptance` },
  { label: '文档解析任务', icon: navAudit, to: `/projects/${projectId.value}/settings/doc-parse-jobs` },
  { label: 'DevOps 流水线', icon: navIntegrations, to: `/projects/${projectId.value}/settings/devops` },
  { label: '测试执行器', icon: navCases, to: `/projects/${projectId.value}/settings/executors` },
  { label: 'AI 能力中心', icon: navAsset, to: `/projects/${projectId.value}/settings/ai-capabilities` },
  { label: '审计日志', icon: navAudit, to: '/settings/audit' }
])

const activeGroupLabel = computed(() => {
  const activeLabel = resolvedActiveAssetChild.value
  if (activeLabel === '设置' || settingsLinks.value.some((item) => item.label === activeLabel)) return '设置'
  const group = groups.value.find((item) => item.label === activeLabel || item.children.some((child) => child.label === activeLabel))
  return group?.label || ''
})

watch(
  activeGroupLabel,
  (label) => {
    activeExpandedGroup.value = label
  },
  { immediate: true }
)
</script>

<template>
  <aside class="flex h-full min-h-screen w-full flex-col bg-[#FAFAFA] border-r border-[#E5E5E5] transition-all duration-300 ease-in-out">
    <div class="flex h-[66.17px] items-center gap-[10px] border-b border-[#E5E5E5] px-[12px]" :class="isCollapsed ? 'justify-center' : ''">
      <div class="flex h-[28px] w-[28px] flex-shrink-0 items-center justify-center rounded-[10px] bg-[#155DFC]">
        <img :src="sidebarLogo" alt="" class="h-[15px] w-[15px]" />
      </div>

      <div v-if="!isCollapsed" class="flex min-w-0 flex-1 flex-col">
        <div class="text-[14px] font-semibold leading-[1.25] text-[#0A0A0A]">WeiTesting</div>
        <div class="text-[12px] leading-[16px] text-[rgba(10,10,10,0.5)]">v1.0.0</div>
      </div>

      <button
        type="button"
        class="flex h-[28px] w-[28px] items-center justify-center rounded-[8px] text-[14px] text-[rgba(10,10,10,0.65)] hover:bg-[#F0F0F0]"
        :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
        @click="toggleSidebar"
      >
        {{ isCollapsed ? '›' : '‹' }}
      </button>
    </div>

    <div class="h-[48.67px] border-b border-[#E5E5E5] px-[12px] pt-[8px] pb-[0.67px]">
      <button
        type="button"
        class="flex h-[32px] w-full items-center gap-[8px] rounded-[10px] bg-[#F5F5F5] px-[8px] hover:bg-[#ECECF0]"
        :class="isCollapsed ? 'justify-center' : ''"
        aria-label="切换项目"
        @click="openProjectSwitcher"
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
          <button
            type="button"
            class="flex h-[36px] items-center gap-[8px] rounded-[10px] px-[12px] hover:bg-[#F5F5F5]"
            :class="isCollapsed ? 'justify-center px-0' : ''"
            :aria-expanded="isGroupExpanded(group.label)"
            @click="toggleGroup(group.label)"
          >
            <img :src="group.icon" alt="" class="h-[16px] w-[16px] flex-shrink-0" />
            <span v-if="!isCollapsed" class="flex-1 text-left text-[14px] leading-[20px] font-medium text-[rgba(10,10,10,0.7)]">
              {{ group.label }}
            </span>
            <img
              v-if="!isCollapsed"
              :src="group.chevron"
              alt=""
              class="h-[14px] w-[14px] transition-transform"
              :class="isGroupExpanded(group.label) ? 'rotate-0' : '-rotate-90'"
            />
          </button>

          <div v-if="isGroupExpanded(group.label)" class="ml-[16px] mt-[4px] flex w-[174.67px] flex-col gap-[2px]">
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

      <div class="mx-[8px] mt-[10px] border-t border-[#E5E5E5] pt-[10px]">
        <button
          type="button"
          class="flex h-[30px] w-full items-center gap-[8px] rounded-[10px] px-[12px] hover:bg-[#F5F5F5]"
          :class="isCollapsed ? 'justify-center px-0' : ''"
          :aria-expanded="activeExpandedGroup === '设置' && !isCollapsed"
          @click="toggleSettings"
        >
          <img :src="navIntegrations" alt="" class="h-[16px] w-[16px] flex-shrink-0" />
          <span v-if="!isCollapsed" class="flex-1 text-left text-[12px] leading-[16px] text-[rgba(10,10,10,0.55)]">设置</span>
          <img
            v-if="!isCollapsed"
            :src="chevronDownSmall"
            alt=""
            class="h-[13px] w-[13px] transition-transform"
            :class="activeExpandedGroup === '设置' ? 'rotate-0' : '-rotate-90'"
          />
        </button>
        <div v-if="!isCollapsed && activeExpandedGroup === '设置'" class="mt-[6px] flex flex-col gap-[2px]">
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
