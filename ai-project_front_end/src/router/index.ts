import { defineAsyncComponent, defineComponent, h } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'

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
const Environments = defineAsyncComponent(() => import('@/views/settings/Environments.vue'))
const PlatformRecords = defineAsyncComponent(() => import('@/views/settings/PlatformRecords.vue'))
const Integrations = defineAsyncComponent(() => import('@/views/settings/Integrations.vue'))
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
const RequirementAnalysisHome = defineAsyncComponent(() => import('@/views/ai/RequirementAnalysisHome.vue'))
const ChangeImpactHome = defineAsyncComponent(() => import('@/views/ai/ChangeImpactHome.vue'))
const SecurityAudit = defineAsyncComponent(() => import('@/views/settings/SecurityAudit.vue'))
const CiTokenGovernance = defineAsyncComponent(() => import('@/views/settings/CiTokenGovernance.vue'))
const AiCapabilities = defineAsyncComponent(() => import('@/views/settings/AiCapabilities.vue'))
const OpsHealth = defineAsyncComponent(() => import('@/views/settings/OpsHealth.vue'))
const AcceptanceCenter = defineAsyncComponent(() => import('@/views/settings/AcceptanceCenter.vue'))
const WorkspaceSectionHome = defineAsyncComponent(() => import('@/views/workspace/WorkspaceSectionHome.vue'))
const Rbac = defineAsyncComponent(() => import('@/views/settings/Rbac.vue'))

const LoginRoute = () => import('../views/Login.vue')
const HomeRoute = () => import('../views/Home.vue')
const CollectionDetailRoute = () => import('@/views/collections/CollectionDetail.vue')
const AiTestingPlatform16_3Route = () => import('@/views/figma/AiTestingPlatform16_3.vue')

const LAST_PROJECT_ID_STORAGE_KEY = 'weitesting:lastProjectId'

function normalizeProjectId(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function resolvePreferredProjectId(explicitProjectId?: unknown): string {
  const explicit = normalizeProjectId(explicitProjectId)
  if (explicit) return explicit
  if (typeof window !== 'undefined') {
    const saved = normalizeProjectId(window.localStorage.getItem(LAST_PROJECT_ID_STORAGE_KEY))
    if (saved) return saved
  }
  return '1'
}

function buildLegacyProjectPath(suffix: string, explicitProjectId?: unknown): string {
  const projectId = resolvePreferredProjectId(explicitProjectId)
  return `/projects/${encodeURIComponent(projectId)}/${suffix}`
}

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
const ProjectAiAssistant = createProjectShellPage('自动生成测试用例', AiAssistantPanel)
const ProjectAiRequirementsHome = createProjectShellPage('需求解析', RequirementAnalysisHome)
const ProjectAiCaseGovernance = createProjectShellPage('用例治理', TrialOperation)
const ProjectAiChangeImpactHome = createProjectShellPage('变更影响分析', ChangeImpactHome)
const ProjectRequirementDocs = createProjectShellPage('需求管理', RequirementDocs)
const ProjectRequirementDocDetail = createProjectShellPage('需求管理', RequirementDocDetail)
const ProjectRequirementAnalysisDetail = createProjectShellPage('需求解析', RequirementAnalysisDetail)
const ProjectRequirementChangeSetDetail = createProjectShellPage('变更影响分析', RequirementChangeSetDetail)
const ProjectKnowledgeRetrospectives = createProjectShellPage('知识沉淀', KnowledgeRetrospectives)
const ProjectPlatformRecords = createProjectShellPage('平台配置', PlatformRecords)
const ProjectIntegrations = createProjectShellPage('集成配置', Integrations)
const ProjectDefectsList = createProjectShellPage('缺陷管理', DefectsList)
const ProjectDefectDetail = createProjectShellPage('缺陷管理', DefectDetail)
const ProjectAutomationApi = createProjectShellPage('接口自动化', ApiCollectionsPanel)
const ProjectAutomationUi = createProjectShellPage('UI自动化', ReportsPanel)
const ProjectAutomationPerformance = createProjectShellPage('性能自动化', ReportsPanel)
const ProjectReportsCenter = createProjectShellPage('报告中心', ReportsPanel)
const ProjectAllureReportsCenter = createProjectShellPage('报告中心', AllureReportPanel)
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
const ProjectRbac = createProjectShellPage('权限', Rbac)

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
      component: LoginRoute
    },
    {
      path: '/register',
      redirect: '/login'
    },
    {
      path: '/projects',
      name: 'Projects',
      component: HomeRoute
    },
    {
      path: '/home',
      redirect: '/projects'
    },
    {
      path: '/projects/:projectId',
      redirect: (to) => `/projects/${encodeURIComponent(String(to.params.projectId))}/dashboard`
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
      component: CollectionDetailRoute
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
      component: ProjectAiRequirementsHome
    },
    {
      path: '/projects/:projectId/ai/case-governance',
      component: ProjectAiCaseGovernance
    },
    {
      path: '/projects/:projectId/ai/change-impact',
      component: ProjectAiChangeImpactHome
    },
    {
      path: '/projects/:projectId/automation/ui',
      component: ProjectAutomationUi
    },
    {
      path: '/projects/:projectId/automation/api',
      component: ProjectAutomationApi
    },
    {
      path: '/projects/:projectId/automation/performance',
      component: ProjectAutomationPerformance
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
      redirect: (to) => `/projects/${encodeURIComponent(String(to.params.projectId))}/automation`
    },
    {
      path: '/projects/:projectId/reports',
      component: ProjectReportsCenter
    },
    {
      path: '/projects/:projectId/reports/allure',
      component: ProjectAllureReportsCenter
    },
    {
      path: '/projects/:projectId/ai-assistant',
      redirect: (to) => `/projects/${encodeURIComponent(String(to.params.projectId))}/ai/generate-cases`
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
      path: '/projects/:projectId/settings/rbac',
      component: ProjectRbac
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
      path: '/projects/:projectId/settings/audit',
      component: createProjectShellPage('审计日志', SecurityAudit)
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
      redirect: () => buildLegacyProjectPath('settings/integrations')
    },
    {
      path: '/settings/rbac',
      redirect: () => buildLegacyProjectPath('settings/rbac')
    },
    {
      path: '/settings/audit',
      redirect: () => buildLegacyProjectPath('settings/audit')
    },
    {
      path: '/dashboard',
      redirect: () => buildLegacyProjectPath('dashboard')
    },
    {
      path: '/dashboard/overview',
      redirect: () => buildLegacyProjectPath('dashboard')
    },
    {
      path: '/figma/untitled-34-158',
      redirect: () => buildLegacyProjectPath('assets/testcases')
    },
    {
      path: '/figma/untitled-13-3',
      redirect: () => buildLegacyProjectPath('assets/testcases')
    },
    {
      path: '/figma/untitled-47-1415',
      redirect: () => buildLegacyProjectPath('assets/suites')
    },
    {
      path: '/figma/untitled-88-3',
      redirect: () => buildLegacyProjectPath('assets/apis')
    },
    {
      path: '/figma/untitled-97-879',
      redirect: () => buildLegacyProjectPath('assets/data')
    },
    {
      path: '/figma/untitled-140-6408',
      redirect: () => buildLegacyProjectPath('assets/suites')
    },
    {
      path: '/figma/untitled-9-3',
      redirect: () => buildLegacyProjectPath('assets/testcases')
    },
    {
      path: '/figma/ai-testing-platform-16-3',
      component: AiTestingPlatform16_3Route
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

router.afterEach((to) => {
  if (typeof window === 'undefined') return
  const projectId = normalizeProjectId(to.params.projectId)
  if (projectId) {
    window.localStorage.setItem(LAST_PROJECT_ID_STORAGE_KEY, projectId)
  }
})

export default router
