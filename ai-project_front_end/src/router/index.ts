import { defineAsyncComponent, defineComponent, h } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import AiTestingPlatformShell from '@/components/figma/ai-testing-platform/AiTestingPlatformShell.vue'

const Login = defineAsyncComponent(() => import('../views/Login.vue'))
const Home = defineAsyncComponent(() => import('../views/Home.vue'))
const Overview = defineAsyncComponent(() => import('../views/dashboard/Overview.vue'))
const CasesPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/CasesPanel.vue'))
const SuitesPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/SuitesPanel.vue'))
const ApiCollectionsPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/ApiCollectionsPanel.vue'))
const DataSetsPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/DataSetsPanel.vue'))
const RunsPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/RunsPanel.vue'))
const WorkersPanel = defineAsyncComponent(() => import('@/components/figma/ai-testing-platform/WorkersPanel.vue'))
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
const Members = defineAsyncComponent(() => import('@/views/settings/Members.vue'))
const SecurityAudit = defineAsyncComponent(() => import('@/views/settings/SecurityAudit.vue'))
const CiTokenGovernance = defineAsyncComponent(() => import('@/views/settings/CiTokenGovernance.vue'))
const AiCapabilities = defineAsyncComponent(() => import('@/views/settings/AiCapabilities.vue'))
const TaskQueue = defineAsyncComponent(() => import('@/views/settings/TaskQueue.vue'))
const AlertRules = defineAsyncComponent(() => import('@/views/settings/AlertRules.vue'))
const DefectProviders = defineAsyncComponent(() => import('@/views/settings/DefectProviders.vue'))
const NotificationProviders = defineAsyncComponent(() => import('@/views/settings/NotificationProviders.vue'))
const CiCdConfig = defineAsyncComponent(() => import('@/views/settings/CiCdConfig.vue'))
const ApiDocs = defineAsyncComponent(() => import('@/views/settings/ApiDocs.vue'))
const UiAutomation = defineAsyncComponent(() => import('@/views/settings/UiAutomation.vue'))
const PerformanceTests = defineAsyncComponent(() => import('@/views/settings/PerformanceTests.vue'))
const AiTraining = defineAsyncComponent(() => import('@/views/settings/AiTraining.vue'))
const KnowledgeTemplates = defineAsyncComponent(() => import('@/views/knowledge/KnowledgeTemplates.vue'))

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
const ProjectTestCases = createProjectShellPage('用例管理', CasesPanel)
const ProjectTestCaseDetail = createProjectShellPage('用例管理', TestCaseDetailPanel)
const ProjectSuites = createProjectShellPage('测试套件', SuitesPanel)
const ProjectSuiteDetail = createProjectShellPage('测试套件', SuiteDetailPanel)
const ProjectApis = createProjectShellPage('接口集合', ApiCollectionsPanel)
const ProjectDataSets = createProjectShellPage('测试数据', DataSetsPanel)
const ProjectRuns = createProjectShellPage('运行记录', RunsPanel)
const ProjectRunDetail = createProjectShellPage('运行记录', RunDetail)
const ProjectWorkers = createProjectShellPage('Worker 管理', WorkersPanel)
const ProjectReports = createProjectShellPage('', ReportsPanel)
const ProjectAllureReport = createProjectShellPage('', AllureReportPanel)
const ProjectAiAssistant = createProjectShellPage('AI 助手', AiAssistantPanel)
const ProjectRequirementDocs = createProjectShellPage('需求文档中心', RequirementDocs)
const ProjectRequirementDocDetail = createProjectShellPage('需求文档中心', RequirementDocDetail)
const ProjectRequirementAnalysisDetail = createProjectShellPage('需求文档中心', RequirementAnalysisDetail)
const ProjectRequirementChangeSetDetail = createProjectShellPage('需求文档中心', RequirementChangeSetDetail)
const ProjectKnowledgeRetrospectives = createProjectShellPage('知识中心', KnowledgeRetrospectives)
const ProjectPlatformRecords = createProjectShellPage('平台记录', PlatformRecords)
const ProjectIntegrations = createProjectShellPage('集成配置', Integrations)
const ProjectDefectsList = createProjectShellPage('缺陷管理', DefectsList)
const ProjectDefectDetail = createProjectShellPage('缺陷管理', DefectDetail)

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
      component: CollectionDetail
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
      component: ProjectRunDetail
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
      component: createProjectShellPage('环境管理', Environments)
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
      path: '/projects/:projectId/settings/task-queue',
      component: createProjectShellPage('任务队列监控', TaskQueue)
    },
    {
      path: '/projects/:projectId/settings/alert-rules',
      component: createProjectShellPage('告警规则', AlertRules)
    },
    {
      path: '/projects/:projectId/settings/defect-providers',
      component: createProjectShellPage('缺陷系统对接', DefectProviders)
    },
    {
      path: '/projects/:projectId/settings/notification-providers',
      component: createProjectShellPage('通知 Provider 配置', NotificationProviders)
    },
    {
      path: '/projects/:projectId/settings/cicd-config',
      component: createProjectShellPage('CI/CD 配置中心', CiCdConfig)
    },
    {
      path: '/projects/:projectId/settings/api-docs',
      component: createProjectShellPage('API 文档', ApiDocs)
    },
    {
      path: '/projects/:projectId/settings/ui-automation',
      component: createProjectShellPage('UI 自动化录制', UiAutomation)
    },
    {
      path: '/projects/:projectId/settings/performance-tests',
      component: createProjectShellPage('性能测试平台', PerformanceTests)
    },
    {
      path: '/projects/:projectId/settings/ai-training',
      component: createProjectShellPage('AI 模型训练', AiTraining)
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
      path: '/projects/:projectId/knowledge/templates',
      component: createProjectShellPage('知识中心', KnowledgeTemplates)
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
      component: createProjectShellPage('权限与成员', Members)
    },
    {
      path: '/settings/audit',
      component: createProjectShellPage('安全审计', SecurityAudit)
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
