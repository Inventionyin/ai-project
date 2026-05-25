import { defineAsyncComponent, defineComponent, h } from 'vue'
import { createRouter, createWebHistory, useRoute } from 'vue-router'
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'

const Login = defineAsyncComponent(() => import('../views/Login.vue'))
const Home = defineAsyncComponent(() => import('../views/Home.vue'))
const Overview = defineAsyncComponent(() => import('../views/dashboard/Overview.vue'))
const TrialOperation = defineAsyncComponent(() => import('../views/dashboard/TrialOperation.vue'))
const CasesPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/CasesPanel.vue'))
const SuitesPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/SuitesPanel.vue'))
const ApiCollectionsPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/ApiCollectionsPanel.vue'))
const DataSetsPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/DataSetsPanel.vue'))
const RunsPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/RunsPanel.vue'))
const SuiteDetailPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/SuiteDetailPanel.vue'))
const ReportsPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/ReportsPanel.vue'))
const AllureReportPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/AllureReportPanel.vue'))
const TestCaseDetailPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/TestCaseDetailPanel.vue'))
const AiAssistantPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/AiAssistantPanel.vue'))
const RunDetail = defineAsyncComponent(() => import('@/views/runs/RunDetail.vue'))
const AiTestingPlatform16_3 = defineAsyncComponent(() => import('@/views/figma/AiTestingPlatform16_3.vue'))
const Environments = defineAsyncComponent(() => import('@/views/settings/Environments.vue'))
const PlatformRecords = defineAsyncComponent(() => import('@/views/settings/PlatformRecords.vue'))
const Integrations = defineAsyncComponent(() => import('@/views/settings/Integrations.vue'))
const CollectionDetail = defineAsyncComponent(() => import('@/views/collections/CollectionDetail.vue'))
const RequirementDocs = defineAsyncComponent(() => import('@/views/requirements/RequirementDocs.vue'))
const RequirementDocDetail = defineAsyncComponent(() => import('@/views/requirements/RequirementDocDetail.vue'))
const RequirementAnalysisDetail = defineAsyncComponent(() => import('@/views/requirements/RequirementAnalysisDetail.vue'))
const RequirementChangeSetDetail = defineAsyncComponent(() => import('@/views/requirements/RequirementChangeSetDetail.vue'))
const KnowledgeRetrospectives = defineAsyncComponent(() => import('@/views/knowledge/KnowledgeRetrospectives.vue'))
const DefectsList = defineAsyncComponent(() => import('@/views/defects/DefectsList.vue'))
const DefectDetail = defineAsyncComponent(() => import('@/views/defects/DefectDetail.vue'))
const DocParseJobs = defineAsyncComponent(() => import('@/views/settings/DocParseJobs.vue'))
const DevOps = defineAsyncComponent(() => import('@/views/settings/DevOps.vue'))
const Executors = defineAsyncComponent(() => import('@/views/settings/Executors.vue'))
const Plugins = defineAsyncComponent(() => import('@/views/settings/Plugins.vue'))
const SecurityAudit = defineAsyncComponent(() => import('@/views/settings/SecurityAudit.vue'))
const CiTokenGovernance = defineAsyncComponent(() => import('@/views/settings/CiTokenGovernance.vue'))
const AiCapabilities = defineAsyncComponent(() => import('@/views/settings/AiCapabilities.vue'))
const OpsHealth = defineAsyncComponent(() => import('@/views/settings/OpsHealth.vue'))
const AcceptanceCenter = defineAsyncComponent(() => import('@/views/settings/AcceptanceCenter.vue'))
const Rbac = defineAsyncComponent(() => import('@/views/settings/Rbac.vue'))
const WorkspaceSectionHome = defineAsyncComponent(() => import('@/views/workspace/WorkspaceSectionHome.vue'))

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
const ProjectTrialOperation = createProjectShellPage('试运行看板', TrialOperation)
const ProjectTestCases = createProjectShellPage('用例管理', CasesPanel)
const ProjectTestCaseDetail = createProjectShellPage('用例管理', TestCaseDetailPanel)
const ProjectSuites = createProjectShellPage('测试套件', SuitesPanel)
const ProjectSuiteDetail = createProjectShellPage('测试套件', SuiteDetailPanel)
const ProjectApis = createProjectShellPage('接口管理', ApiCollectionsPanel)
const ProjectDataSets = createProjectShellPage('测试数据', DataSetsPanel)
const ProjectRuns = createProjectShellPage('运行记录', RunsPanel)
const ProjectRunDetail = createProjectShellPage('运行记录', RunDetail)
const ProjectReports = createProjectShellPage('', ReportsPanel)
const ProjectAllureReport = createProjectShellPage('', AllureReportPanel)
const ProjectAiAssistant = createProjectShellPage('自动生成测试用例', AiAssistantPanel)
const ProjectRequirementDocs = createProjectShellPage('需求管理', RequirementDocs)
const ProjectRequirementDocDetail = createProjectShellPage('需求管理', RequirementDocDetail)
const ProjectRequirementAnalysisDetail = createProjectShellPage('需求解析', RequirementAnalysisDetail)
const ProjectRequirementChangeSetDetail = createProjectShellPage('变更影响分析', RequirementChangeSetDetail)
const ProjectKnowledgeRetrospectives = createProjectShellPage('知识沉淀', KnowledgeRetrospectives)
const ProjectPlatformRecords = createProjectShellPage('平台记录', PlatformRecords)
const ProjectIntegrations = createProjectShellPage('集成配置', Integrations)
const ProjectDefectsList = createProjectShellPage('缺陷管理', DefectsList)
const ProjectDefectDetail = createProjectShellPage('缺陷管理', DefectDetail)
const ProjectAssetsHome = createProjectShellPage('资产中心', defineComponent({
  name: 'ProjectAssetsHome',
  setup: () => () => h(WorkspaceSectionHome, { section: 'assets' })
}))
const ProjectAiHome = createProjectShellPage('AI能力', defineComponent({
  name: 'ProjectAiHome',
  setup: () => () => h(WorkspaceSectionHome, { section: 'ai' })
}))
const ProjectAutomationHome = createProjectShellPage('自动化执行', defineComponent({
  name: 'ProjectAutomationHome',
  setup: () => () => h(WorkspaceSectionHome, { section: 'automation' })
}))
const ProjectSettingsHome = createProjectShellPage('设置', defineComponent({
  name: 'ProjectSettingsHome',
  setup: () => () => h(WorkspaceSectionHome, { section: 'settings' })
}))

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
      redirect: '/login'
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
      path: '/projects/:projectId/trial-operation',
      component: ProjectTrialOperation
    },
    {
      path: '/projects/:projectId/assets',
      component: ProjectAssetsHome
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
      component: CollectionDetail
    },
    {
      path: '/projects/:projectId/assets/data',
      component: ProjectDataSets
    },
    {
      path: '/projects/:projectId/ai',
      component: ProjectAiHome
    },
    {
      path: '/projects/:projectId/ai/generate-cases',
      component: ProjectAiAssistant
    },
    {
      path: '/projects/:projectId/ai/requirements',
      component: ProjectRequirementDocs
    },
    {
      path: '/projects/:projectId/ai/case-governance',
      component: ProjectTrialOperation
    },
    {
      path: '/projects/:projectId/ai/change-impact',
      component: ProjectRequirementDocs
    },
    {
      path: '/projects/:projectId/automation/ui',
      component: ProjectReports
    },
    {
      path: '/projects/:projectId/automation/api',
      component: ProjectApis
    },
    {
      path: '/projects/:projectId/automation/performance',
      component: ProjectReports
    },
    {
      path: '/projects/:projectId/automation',
      component: ProjectAutomationHome
    },
    {
      path: '/projects/:projectId/runs',
      component: ProjectRuns
    },
    {
      path: '/projects/:projectId/runs/:runId',
      component: ProjectRunDetail
    },
    {
      path: '/projects/:projectId/workers',
      redirect: (to) => `/projects/${String(to.params.projectId)}/automation`
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
      redirect: (to) => `/projects/${String(to.params.projectId)}/ai/generate-cases`
    },
    {
      path: '/projects/:projectId/settings/environments',
      component: createProjectShellPage('环境管理', Environments)
    },
    {
      path: '/projects/:projectId/settings',
      component: ProjectSettingsHome
    },
    {
      path: '/projects/:projectId/settings/platform-records',
      component: ProjectPlatformRecords
    },
    {
      path: '/projects/:projectId/settings/integrations',
      component: ProjectIntegrations
    },
    {
      path: '/projects/:projectId/settings/doc-parse-jobs',
      component: createProjectShellPage('文档解析任务', DocParseJobs)
    },
    {
      path: '/projects/:projectId/settings/devops',
      component: createProjectShellPage('DevOps 流水线', DevOps)
    },
    {
      path: '/projects/:projectId/settings/executors',
      component: createProjectShellPage('测试执行器', Executors)
    },
    {
      path: '/projects/:projectId/settings/plugins',
      component: createProjectShellPage('插件市场', Plugins)
    },
    {
      path: '/projects/:projectId/settings/security-audit',
      component: createProjectShellPage('安全审计', SecurityAudit)
    },
    {
      path: '/projects/:projectId/settings/ci-token-governance',
      component: createProjectShellPage('CI Token 治理', CiTokenGovernance)
    },
    {
      path: '/projects/:projectId/settings/ai-capabilities',
      component: createProjectShellPage('AI 能力中心', AiCapabilities)
    },
    {
      path: '/projects/:projectId/settings/ops-health',
      component: createProjectShellPage('运维健康', OpsHealth)
    },
    {
      path: '/projects/:projectId/settings/acceptance',
      component: createProjectShellPage('验收中心', AcceptanceCenter)
    },
    {
      path: '/projects/:projectId/requirements/docs',
      component: ProjectRequirementDocs
    },
    {
      path: '/projects/:projectId/requirements/docs/:docId',
      component: ProjectRequirementDocDetail
    },
    {
      path: '/projects/:projectId/requirements/analyses/:analysisId',
      component: ProjectRequirementAnalysisDetail
    },
    {
      path: '/projects/:projectId/requirements/change-sets/:changeSetId',
      component: ProjectRequirementChangeSetDetail
    },
    {
      path: '/projects/:projectId/knowledge/retrospectives',
      component: ProjectKnowledgeRetrospectives
    },
    {
      path: '/projects/:projectId/defects',
      component: ProjectDefectsList
    },
    {
      path: '/projects/:projectId/defects/:defectId',
      component: ProjectDefectDetail
    },
    {
      path: '/settings/integrations',
      redirect: '/projects/1/settings/integrations'
    },
    {
      path: '/settings/rbac',
      component: Rbac
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
  if (to.path === '/login') {
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
