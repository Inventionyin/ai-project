<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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

type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
}

type PageData<T> = {
  page: number
  pageSize: number
  total: number
  items: T[]
}

type ProjectListItem = {
  id: string
  name: string
  description?: string | null
  caseCount?: number | null
  createdAt?: number | null
}

const { activeAssetChild, projectName = '项目' } = defineProps<{
  activeAssetChild?: string
  projectName?: string
}>()

const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const expandedGroups = ref<Set<string>>(new Set(['资产中心', '执行中心']))
const isProjectMenuOpen = ref(false)
const isLoadingProjects = ref(false)
const projectMenuError = ref('')
const projectOptions = ref<ProjectListItem[]>([])
const projectSwitcherRef = ref<HTMLElement | null>(null)

function toggleGroup(label: string) {
  if (expandedGroups.value.has(label)) {
    expandedGroups.value.delete(label)
  } else {
    expandedGroups.value.add(label)
  }
}

function navigateTo(item: LinkItem) {
  if (!item.to) return
  router.push(item.to)
}

const projectId = computed(() => {
  const id = route.params.projectId
  return typeof id === 'string' && id.length > 0 ? id : '1'
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

const loadProjectOptions = async () => {
  if (isLoadingProjects.value) return
  isLoadingProjects.value = true
  projectMenuError.value = ''
  try {
    const response = await fetch(`${resolveApiBaseUrl()}/api/projects?page=1&pageSize=200`, {
      method: 'GET',
      headers: {
        Authorization: resolveAuthHeader()
      }
    })
    const payload = (await response.json()) as ApiResponse<PageData<ProjectListItem>>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '获取项目列表失败')
    }
    projectOptions.value = payload.data.items
  } catch (error) {
    projectMenuError.value = error instanceof Error ? error.message : '获取项目列表失败'
  } finally {
    isLoadingProjects.value = false
  }
}

const toggleProjectMenu = async () => {
  isProjectMenuOpen.value = !isProjectMenuOpen.value
  if (isProjectMenuOpen.value && projectOptions.value.length === 0) {
    await loadProjectOptions()
  }
}

const switchProject = (nextProjectId: string) => {
  const nextId = String(nextProjectId || '').trim()
  if (!nextId) return
  isProjectMenuOpen.value = false
  if (nextId === projectId.value) return
  const currentPath = route.path
  const nextPath = currentPath.startsWith(`/projects/${projectId.value}`)
    ? currentPath.replace(`/projects/${projectId.value}`, `/projects/${nextId}`)
    : `/projects/${nextId}/dashboard`
  router.push({ path: nextPath, query: route.query })
}

const onWindowClick = (event: MouseEvent) => {
  if (!isProjectMenuOpen.value) return
  const target = event.target as Node | null
  if (!target) return
  if (projectSwitcherRef.value?.contains(target)) return
  isProjectMenuOpen.value = false
}

const resolvedActiveAssetChild = computed(() => {
  if (typeof activeAssetChild === 'string') return activeAssetChild
  if (route.path.startsWith(`/projects/${projectId.value}/assets/suites`)) return '测试套件'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/testcases`)) return '用例管理'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/apis`)) return '接口集合'
  if (route.path.startsWith(`/projects/${projectId.value}/assets/data`)) return '测试数据'
  if (route.path.startsWith(`/projects/${projectId.value}/trial-operation`)) return '试运行看板'
  if (route.path.startsWith(`/projects/${projectId.value}/runs`)) return '运行记录'
  if (route.path.startsWith(`/projects/${projectId.value}/workers`)) return 'Worker 管理'
  if (route.path.startsWith(`/projects/${projectId.value}/ai-assistant`)) return 'AI 助手'
  if (route.path.startsWith(`/projects/${projectId.value}/requirements/docs`)) return '需求文档中心'
  if (route.path.startsWith(`/projects/${projectId.value}/defects`)) return '缺陷管理'
  if (route.path.startsWith(`/projects/${projectId.value}/knowledge`)) return '知识中心'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/platform-records`)) return '平台记录'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/integrations`)) return '集成配置'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/doc-parse-jobs`)) return '文档解析任务'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/devops`)) return 'DevOps 流水线'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/executors`)) return '测试执行器'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/plugins`)) return '插件市场'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/security-audit`)) return '安全审计'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/ci-token-governance`)) return 'CI Token 治理'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/ai-capabilities`)) return 'AI 能力中心'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/task-queue`)) return '任务队列监控'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/alert-rules`)) return '告警规则'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/defect-providers`)) return '缺陷系统对接'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/notification-providers`)) return '通知 Provider 配置'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/cicd-config`)) return 'CI/CD 配置中心'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/api-docs`)) return 'API 文档'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/ui-automation`)) return 'UI 自动化录制'
  if (route.path.startsWith(`/projects/${projectId.value}/settings/performance-tests`)) return '性能测试平台'
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
  { label: '仪表盘', icon: navDashboard, to: `/projects/${projectId.value}/dashboard` },
  { label: '试运行看板', icon: navDashboard, to: `/projects/${projectId.value}/trial-operation` }
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
  { label: '缺陷管理', icon: navAudit, to: `/projects/${projectId.value}/defects` },
  { label: '知识中心', icon: navAudit, to: `/projects/${projectId.value}/knowledge/retrospectives` },
  { label: '知识模板', icon: navAudit, to: `/projects/${projectId.value}/knowledge/templates` },
  { label: 'AI 助手', icon: navAiAssistant, to: `/projects/${projectId.value}/ai-assistant` }
])

type SettingsGroup = {
  label: string
  children: LinkItem[]
}

const settingsGroups = computed<SettingsGroup[]>(() => {
  const p = projectId.value
  return [
    {
      label: '基础配置',
      children: [
        { label: '平台记录', icon: navAudit, to: `/projects/${p}/settings/platform-records` },
        { label: '环境管理', icon: navEnv, to: `/projects/${p}/settings/environments` },
        { label: '成员权限', icon: navMember, to: '/settings/rbac' },
      ]
    },
    {
      label: '集成与对接',
      children: [
        { label: '集成配置', icon: navIntegrations, to: `/projects/${p}/settings/integrations` },
        { label: '缺陷系统对接', icon: navIntegrations, to: `/projects/${p}/settings/defect-providers` },
        { label: '通知 Provider', icon: navIntegrations, to: `/projects/${p}/settings/notification-providers` },
        { label: 'CI/CD 配置中心', icon: navIntegrations, to: `/projects/${p}/settings/cicd-config` },
        { label: 'DevOps 流水线', icon: navIntegrations, to: `/projects/${p}/settings/devops` },
      ]
    },
    {
      label: '测试能力',
      children: [
        { label: '测试执行器', icon: navCases, to: `/projects/${p}/settings/executors` },
        { label: '文档解析任务', icon: navAudit, to: `/projects/${p}/settings/doc-parse-jobs` },
        { label: 'UI 自动化录制', icon: navCases, to: `/projects/${p}/settings/ui-automation` },
        { label: '性能测试平台', icon: navCases, to: `/projects/${p}/settings/performance-tests` },
      ]
    },
    {
      label: '安全与监控',
      children: [
        { label: '审计日志', icon: navAudit, to: '/settings/audit' },
        { label: '安全审计', icon: navAudit, to: `/projects/${p}/settings/security-audit` },
        { label: 'CI Token 治理', icon: navIntegrations, to: `/projects/${p}/settings/ci-token-governance` },
        { label: '任务队列', icon: navAudit, to: `/projects/${p}/settings/task-queue` },
        { label: '告警规则', icon: navAudit, to: `/projects/${p}/settings/alert-rules` },
      ]
    },
    {
      label: '扩展与文档',
      children: [
        { label: '插件市场', icon: navAsset, to: `/projects/${p}/settings/plugins` },
        { label: 'AI 能力中心', icon: navAsset, to: `/projects/${p}/settings/ai-capabilities` },
        { label: 'API 文档', icon: navIntegrations, to: `/projects/${p}/settings/api-docs` },
      ]
    },
  ]
})

const expandedSettingsGroups = ref<Set<string>>(new Set())

function toggleSettingsGroup(label: string) {
  if (expandedSettingsGroups.value.has(label)) {
    expandedSettingsGroups.value.delete(label)
  } else {
    expandedSettingsGroups.value.add(label)
  }
}

onMounted(() => {
  window.addEventListener('click', onWindowClick, true)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick, true)
})

watch(projectId, () => {
  isProjectMenuOpen.value = false
})
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

    <div ref="projectSwitcherRef" class="relative h-[48.67px] border-b border-[#E5E5E5] px-[12px] pt-[8px] pb-[0.67px]">
      <button
        type="button"
        class="flex h-[32px] w-full items-center gap-[8px] rounded-[10px] bg-[#F5F5F5] px-[8px]"
        :class="isCollapsed ? 'justify-center' : ''"
        @click.stop="toggleProjectMenu"
      >
        <span class="flex h-[20px] w-[20px] items-center justify-center rounded-[4px] bg-[#DBEAFE] flex-shrink-0">
          <img :src="projectIcon" alt="" class="h-[12px] w-[12px]" />
        </span>
        <span v-if="!isCollapsed" class="flex-1 text-left text-[14px] leading-[20px] font-medium text-[#0A0A0A]">{{ projectName }}</span>
        <img v-if="!isCollapsed" :src="chevronDownSmall" alt="" class="h-[13px] w-[13px] transition-transform" :class="isProjectMenuOpen ? 'rotate-180' : ''" />
      </button>

      <div
        v-if="!isCollapsed && isProjectMenuOpen"
        class="absolute left-[12px] right-[12px] top-[44px] z-50 overflow-hidden rounded-[10px] border border-black/10 bg-white shadow-[0px_10px_15px_-3px_rgba(0,0,0,0.1),0px_4px_6px_-4px_rgba(0,0,0,0.1)]"
      >
        <div v-if="isLoadingProjects" class="px-[12px] py-[10px] text-[12px] leading-[16px] text-[#717182]">加载项目中...</div>
        <div v-else-if="projectMenuError" class="px-[12px] py-[10px] text-[12px] leading-[16px] text-[#B45309]">{{ projectMenuError }}</div>
        <div v-else-if="projectOptions.length === 0" class="px-[12px] py-[10px] text-[12px] leading-[16px] text-[#717182]">暂无项目</div>
        <div v-else class="max-h-[260px] overflow-auto py-[4px]">
          <button
            v-for="project in projectOptions"
            :key="project.id"
            type="button"
            class="flex w-full flex-col gap-[2px] px-[12px] py-[8px] text-left hover:bg-[#F6F7F9]"
            :class="project.id === projectId ? 'bg-[#EFF6FF]' : ''"
            @click="switchProject(project.id)"
          >
            <span class="truncate text-[13px] font-medium leading-[18px]" :class="project.id === projectId ? 'text-[#155DFC]' : 'text-[#0A0A0A]'">{{ project.name }}</span>
            <span class="text-[11px] leading-[14px] text-[#717182]">用例 {{ project.caseCount ?? 0 }}</span>
          </button>
        </div>
        <button
          type="button"
          class="block w-full border-t border-black/10 px-[12px] py-[8px] text-left text-[12px] font-medium leading-[16px] text-[#155DFC] hover:bg-[#F6F7F9]"
          @click="router.push('/projects')"
        >
          查看所有项目
        </button>
      </div>
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
          <button type="button" class="flex h-[36px] items-center gap-[8px] rounded-[10px] px-[12px]" :class="isCollapsed ? 'justify-center px-0' : ''" @click="toggleGroup(group.label)">
            <img :src="group.icon" alt="" class="h-[16px] w-[16px] flex-shrink-0" />
            <span v-if="!isCollapsed" class="flex-1 text-left text-[14px] leading-[20px] font-medium text-[rgba(10,10,10,0.7)]">
              {{ group.label }}
            </span>
            <img v-if="!isCollapsed" :src="group.chevron" alt="" class="h-[14px] w-[14px] transition-transform duration-200" :class="expandedGroups.has(group.label) ? '' : 'rotate-180'" />
          </button>

          <div v-if="!isCollapsed && expandedGroups.has(group.label)" class="ml-[16px] mt-[4px] flex w-[174.67px] flex-col gap-[2px]">
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
          <div v-for="group in settingsGroups" :key="group.label">
            <button
              v-if="!isCollapsed"
              type="button"
              class="flex h-[32px] w-full items-center gap-[6px] rounded-[8px] px-[12px] mb-[2px]"
              @click="toggleSettingsGroup(group.label)"
            >
              <img :src="navChevron" alt="" class="h-[12px] w-[12px] flex-shrink-0 transition-transform duration-200" :class="expandedSettingsGroups.has(group.label) ? 'rotate-90' : ''" />
              <span class="text-[12px] leading-[16px] font-medium text-[rgba(10,10,10,0.45)]">{{ group.label }}</span>
            </button>
            <div v-if="isCollapsed || expandedSettingsGroups.has(group.label)">
              <button
                v-for="item in group.children"
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
        </div>
      </div>
    </nav>

  </aside>
</template>
