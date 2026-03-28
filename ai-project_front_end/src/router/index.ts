import { defineComponent, h } from 'vue'
import { createRouter, createWebHistory, useRoute } from 'vue-router'
import Login from '../views/Login.vue'
import Home from '../views/Home.vue'
import Overview from '../views/dashboard/Overview.vue'
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'
import CasesPanel from '@/components/figma/ai-testing-platform/CasesPanel.vue'
import SuitesPanel from '@/components/figma/ai-testing-platform/SuitesPanel.vue'
import ApiCollectionsPanel from '@/components/figma/ai-testing-platform/ApiCollectionsPanel.vue'
import DataSetsPanel from '@/components/figma/ai-testing-platform/DataSetsPanel.vue'
import RunsPanel from '@/components/figma/ai-testing-platform/RunsPanel.vue'
import WorkersPanel from '@/components/figma/ai-testing-platform/WorkersPanel.vue'
import SuiteDetailPanel from '@/components/figma/ai-testing-platform/SuiteDetailPanel.vue'
import ReportsPanel from '@/components/figma/ai-testing-platform/ReportsPanel.vue'
import AllureReportPanel from '@/components/figma/ai-testing-platform/AllureReportPanel.vue'
import TestCaseDetailPanel from '@/components/figma/ai-testing-platform/TestCaseDetailPanel.vue'
import AiAssistantPanel from '@/components/figma/ai-testing-platform/AiAssistantPanel.vue'
import AiTestingPlatform16_3 from '@/views/figma/AiTestingPlatform16_3.vue'

function createProjectShellPage(activeAssetChild: string, Content: Parameters<typeof h>[0]) {
  return defineComponent({
    name: `ProjectShellPage_${activeAssetChild || 'Dashboard'}`,
    setup() {
      return () =>
        h(
          AiTestingPlatformShell,
          { activeAssetChild },
          typeof Content === 'string'
            ? undefined
            : {
                default: () => h(Content)
              }
        )
    }
  })
}

function createPlaceholderPage(title: string) {
  return defineComponent({
    name: `Placeholder_${title}`,
    setup() {
      const route = useRoute()
      return () =>
        h('div', { class: 'min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6' }, [
          h('div', { class: 'rounded-[14px] border border-black/10 bg-white p-6' }, [
            h('div', { class: 'text-[14px] font-semibold leading-[20px] text-[#0A0A0A]' }, title),
            h(
              'div',
              { class: 'mt-2 text-[12px] leading-[16px] text-[#717182]' },
              `projectId: ${String(route.params.projectId ?? '-')}${route.params.id ? ` · id: ${String(route.params.id)}` : ''}${route.params.runId ? ` · runId: ${String(route.params.runId)}` : ''}`
            )
          ])
        ])
    }
  })
}

const ProjectDashboard = createProjectShellPage('', Overview)
const ProjectTestCases = createProjectShellPage('用例管理', CasesPanel)
const ProjectTestCaseDetail = createProjectShellPage('用例管理', TestCaseDetailPanel)
const ProjectSuites = createProjectShellPage('测试套件', SuitesPanel)
const ProjectSuiteDetail = createProjectShellPage('测试套件', SuiteDetailPanel)
const ProjectApis = createProjectShellPage('接口集合', ApiCollectionsPanel)
const ProjectDataSets = createProjectShellPage('测试数据', DataSetsPanel)
const ProjectRuns = createProjectShellPage('运行记录', RunsPanel)
const ProjectWorkers = createProjectShellPage('Worker 管理', WorkersPanel)
const ProjectReports = createProjectShellPage('', ReportsPanel)
const ProjectAllureReport = createProjectShellPage('', AllureReportPanel)
const ProjectAiAssistant = createProjectShellPage('AI 助手', AiAssistantPanel)

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'Login',
      component: Login
    },
    {
      path: '/register',
      redirect: { path: '/login', query: { tab: 'register' } }
    },
    {
      path: '/projects',
      name: 'Projects',
      component: Home
    },
    {
      path: '/home',
      redirect: '/projects'
    },
    {
      path: '/projects/:projectId',
      redirect: (to) => `/projects/${String(to.params.projectId)}/dashboard`
    },
    {
      path: '/projects/:projectId/dashboard',
      component: ProjectDashboard
    },
    {
      path: '/projects/:projectId/assets/testcases',
      component: ProjectTestCases
    },
    {
      path: '/projects/:projectId/assets/testcases/:id',
      component: ProjectTestCaseDetail
    },
    {
      path: '/projects/:projectId/assets/suites',
      component: ProjectSuites
    },
    {
      path: '/projects/:projectId/assets/suites/:id',
      component: ProjectSuiteDetail
    },
    {
      path: '/projects/:projectId/assets/apis',
      component: ProjectApis
    },
    {
      path: '/projects/:projectId/assets/apis/:id',
      component: createPlaceholderPage('接口集合详情')
    },
    {
      path: '/projects/:projectId/assets/data',
      component: ProjectDataSets
    },
    {
      path: '/projects/:projectId/runs',
      component: ProjectRuns
    },
    {
      path: '/projects/:projectId/runs/:runId',
      component: createPlaceholderPage('运行详情（实时）')
    },
    {
      path: '/projects/:projectId/workers',
      component: ProjectWorkers
    },
    {
      path: '/projects/:projectId/reports',
      component: ProjectReports
    },
    {
      path: '/projects/:projectId/reports/allure',
      component: ProjectAllureReport
    },
    {
      path: '/projects/:projectId/ai-assistant',
      component: ProjectAiAssistant
    },
    {
      path: '/projects/:projectId/settings/environments',
      component: createPlaceholderPage('环境管理')
    },
    {
      path: '/settings/integrations',
      component: createPlaceholderPage('集成配置（管理员/Owner）')
    },
    {
      path: '/settings/rbac',
      component: createPlaceholderPage('权限与成员')
    },
    {
      path: '/settings/audit',
      component: createPlaceholderPage('审计日志')
    },
    {
      path: '/dashboard',
      redirect: '/projects/1/dashboard'
    },
    {
      path: '/dashboard/overview',
      redirect: '/projects/1/dashboard'
    },
    {
      path: '/figma/untitled-34-158',
      redirect: '/projects/1/assets/testcases'
    },
    {
      path: '/figma/untitled-13-3',
      redirect: '/projects/1/assets/testcases'
    },
    {
      path: '/figma/untitled-47-1415',
      redirect: '/projects/1/assets/suites'
    },
    {
      path: '/figma/untitled-88-3',
      redirect: '/projects/1/assets/apis'
    },
    {
      path: '/figma/untitled-97-879',
      redirect: '/projects/1/assets/data'
    },
    {
      path: '/figma/untitled-140-6408',
      redirect: '/projects/1/assets/suites/1'
    },
    {
      path: '/figma/untitled-9-3',
      component: ProjectTestCaseDetail
    },
    {
      path: '/figma/ai-testing-platform-16-3',
      component: AiTestingPlatform16_3
    }
  ]
})

router.beforeEach((to) => {
  if (to.path === '/login' || to.path === '/register') {
    return true
  }
  if (to.path.startsWith('/figma/')) {
    return true
  }

  const accessToken = localStorage.getItem('accessToken')
  const expiresAtRaw = localStorage.getItem('accessTokenExpiresAt')
  const expiresAt = expiresAtRaw ? Number(expiresAtRaw) : 0
  const isExpired = !Number.isFinite(expiresAt) || expiresAt <= Date.now()

  if (!accessToken || isExpired) {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('accessTokenExpiresAt')
    return {
      path: '/login',
      query: { redirect: to.fullPath }
    }
  }

  return true
})

export default router
