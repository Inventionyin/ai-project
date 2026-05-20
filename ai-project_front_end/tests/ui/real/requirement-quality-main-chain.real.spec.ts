import { expect, test, type APIRequestContext } from '@playwright/test'

const runRealE2E = process.env.WEITESTING_REAL_E2E === '1'
const apiBaseUrl = process.env.WEITESTING_API_BASE_URL || 'http://127.0.0.1:8000'

type ApiEnvelope<T> = {
  code?: number
  message?: string
  data?: T
}

async function expectApiOk<T>(responsePromise: Promise<import('@playwright/test').APIResponse>, label: string) {
  const response = await responsePromise
  const payload = (await response.json().catch(() => ({}))) as ApiEnvelope<T>
  expect(response.ok(), `${label} HTTP failed: ${response.status()} ${JSON.stringify(payload)}`).toBeTruthy()
  expect(payload.code, `${label} business failed: ${JSON.stringify(payload)}`).toBe(0)
  expect(payload.data, `${label} missing data`).toBeTruthy()
  return payload.data as T
}

async function postJson<T>(request: APIRequestContext, path: string, token: string | null, body: unknown, label: string) {
  return expectApiOk<T>(
    request.post(`${apiBaseUrl}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      data: body
    }),
    label
  )
}

async function putJson<T>(request: APIRequestContext, path: string, token: string, body: unknown, label: string) {
  return expectApiOk<T>(
    request.put(`${apiBaseUrl}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      data: body
    }),
    label
  )
}

async function getJson<T>(request: APIRequestContext, path: string, token: string, label: string) {
  return expectApiOk<T>(
    request.get(`${apiBaseUrl}${path}`, {
      headers: { Authorization: `Bearer ${token}` }
    }),
    label
  )
}

test.describe('real backend requirement quality main chain', () => {
  test.skip(!runRealE2E, 'Set WEITESTING_REAL_E2E=1 and start backend + database to run real integration E2E.')

  test('creates requirement analysis, approved cases, direct HTTP run, defect, and retrospective', async ({ page, request }) => {
    const health = await request.get(`${apiBaseUrl}/health`)
    expect(health.ok(), `Backend health check failed at ${apiBaseUrl}/health`).toBeTruthy()

    const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`.slice(-10)
    const username = `real_chain_${suffix}`
    const phone = `13${suffix.slice(0, 9)}`
    const password = 'RealE2e123'
    const projectName = `真实主链项目 ${suffix}`
    const docTitle = `真实主链需求 ${suffix}`
    const directCaseTitle = `真实健康检查用例 ${suffix}`
    const defectTitle = `真实主链缺陷 ${suffix}`
    const retrospectiveTitle = `真实主链复盘 ${suffix}`

    const registered = await postJson<{ userId: string }>(
      request,
      '/api/auth/register',
      null,
      {
        phone,
        username,
        password,
        confirmPassword: password,
        captcha: '123456'
      },
      'register'
    )

    const login = await postJson<{ accessToken: string; expiresIn: number }>(
      request,
      '/api/auth/login',
      null,
      { username, password },
      'login'
    )
    const token = login.accessToken

    const project = await postJson<{ id: string }>(
      request,
      '/api/projects',
      token,
      {
        name: projectName,
        description: '真实主链 E2E 数据项目',
        ownerId: registered.userId
      },
      'create project'
    )

    const doc = await postJson<{ id: string }>(
      request,
      `/api/projects/${project.id}/requirements/docs`,
      token,
      {
        title: docTitle,
        sourceType: 'PRD',
        status: 'DRAFT',
        tags: ['real-e2e']
      },
      'create requirement doc'
    )

    const requirementText = [
      '# 登录与质量闭环需求',
      '',
      '用户必须可以使用用户名和密码登录系统。',
      '密码错误时必须返回清晰提示，不能泄露敏感字段。',
      '项目成员可以创建需求文档、生成测试点、审核测试用例，并把失败结果沉淀为缺陷和复盘。',
      '边界场景包括空用户名、弱密码、重复提交、接口超时和权限不足。'
    ].join('\n')

    const version = await expectApiOk<{ id: string }>(
      request.post(`${apiBaseUrl}/api/projects/${project.id}/requirements/docs/${doc.id}/versions`, {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
          file: {
            name: `real-chain-${suffix}.md`,
            mimeType: 'text/markdown',
            buffer: Buffer.from(requirementText, 'utf-8')
          },
          changeSummary: '真实主链 E2E 初始版本',
          effectiveScope: '登录、需求分析、缺陷、知识复盘'
        }
      }),
      'upload requirement version'
    )

    await postJson<Record<string, unknown>>(
      request,
      `/api/projects/${project.id}/requirements/docs/${doc.id}/versions/${version.id}/parse`,
      token,
      {},
      'parse requirement version'
    )

    const analysis = await postJson<{ id: string }>(
      request,
      `/api/projects/${project.id}/requirements/docs/${doc.id}/versions/${version.id}/analyze`,
      token,
      { instruction: '重点覆盖权限、异常流程、边界值和回归风险' },
      'analyze requirement version'
    )

    const testPoints = await postJson<Array<{ id: string; title: string; status: string }>>(
      request,
      `/api/projects/${project.id}/requirements/analyses/${analysis.id}/sync-test-points`,
      token,
      {},
      'sync requirement test points'
    )
    expect(testPoints.length, 'expected generated test points').toBeGreaterThan(0)

    await putJson<{ id: string; status: string }>(
      request,
      `/api/projects/${project.id}/requirements/test-points/${testPoints[0].id}`,
      token,
      { status: 'ACCEPTED' },
      'accept first test point'
    )

    const drafts = await postJson<Array<{ id: string; title: string; status: string }>>(
      request,
      `/api/projects/${project.id}/requirements/analyses/${analysis.id}/generate-case-drafts`,
      token,
      { mode: 'ACCEPTED_ONLY', testPointIds: [], forceRegenerate: false },
      'generate case drafts'
    )
    expect(drafts.length, 'expected generated case drafts').toBeGreaterThan(0)

    const approval = await postJson<{ createdTestCaseCount: number; testCaseIds: string[] }>(
      request,
      `/api/projects/${project.id}/requirements/case-drafts/bulk-approve`,
      token,
      { draftIds: drafts.map((draft) => draft.id) },
      'bulk approve case drafts'
    )
    expect(approval.createdTestCaseCount, 'expected approved test cases').toBeGreaterThan(0)
    expect(approval.testCaseIds.length, 'expected approved test case ids').toBeGreaterThan(0)

    const directCase = await postJson<{ id: string }>(
      request,
      '/api/testcases',
      token,
      {
        projectId: project.id,
        title: directCaseTitle,
        type: 'API',
        priority: 'P2',
        status: 'DRAFT',
        tags: ['real-e2e'],
        contentMd: 'GET /health should return ok',
        feature: 'health',
        apiMethod: 'GET',
        apiUrl: '/health',
        apiParams: {},
        apiHeaders: {},
        expectedStatusCode: 200,
        expectedResult: 'ok'
      },
      'create direct runnable testcase'
    )

    const run = await postJson<{ id: string; status: string; metrics?: { total?: number } }>(
      request,
      '/api/runs/from-testcases-http',
      token,
      {
        projectId: project.id,
        envId: null,
        triggerType: 'MANUAL',
        meta: { runnerType: 'HTTP', source: 'real-e2e' },
        items: [{ testcaseId: directCase.id, overrideParams: {} }]
      },
      'create direct HTTP run'
    )
    expect(run.status, 'run should be queued without requiring worker completion').toMatch(/QUEUED|RUNNING|PASSED|FAILED/)
    expect(Number(run.metrics?.total || 0), 'run should include one case').toBeGreaterThan(0)

    const defect = await postJson<{ id: string; title: string }>(
      request,
      `/api/projects/${project.id}/defects`,
      token,
      {
        title: defectTitle,
        description: `真实后端创建，用于验证缺陷列表和详情页面\n[Context] runId=${run.id} | testcaseId=${directCase.id}`,
        severity: 'P2'
      },
      'create defect'
    )

    const retrospective = await postJson<{ id: string; title: string }>(
      request,
      `/api/projects/${project.id}/knowledge/retrospectives`,
      token,
      {
        title: retrospectiveTitle,
        sourceType: 'OTHER',
        status: 'DRAFT',
        problemSummary: '真实主链 E2E 复盘摘要',
        rootCause: '需求、用例、运行、缺陷和知识链路需要共同验证',
        decision: '保留真实 E2E 作为质量闸门',
        actionItems: '继续扩展 runner worker 完整执行断言'
      },
      'create retrospective'
    )

    await getJson<{ id: string }>(request, `/api/projects/${project.id}/requirements/analyses/${analysis.id}`, token, 'verify analysis detail')
    await getJson<{ id: string }>(request, `/api/projects/${project.id}/defects/${defect.id}`, token, 'verify defect detail')
    await getJson<{ id: string }>(request, `/api/projects/${project.id}/knowledge/retrospectives/${retrospective.id}`, token, 'verify retrospective detail')

    await page.addInitScript(
      ({ accessToken, expiresAt }) => {
        localStorage.setItem('accessToken', accessToken)
        localStorage.setItem('accessTokenExpiresAt', String(expiresAt))
      },
      { accessToken: token, expiresAt: Date.now() + Math.max(60, login.expiresIn || 3600) * 1000 }
    )

    await page.goto(`/projects/${project.id}/requirements/docs`)
    await expect(page.locator('div').filter({ hasText: /^需求文档中心$/ })).toBeVisible()
    await expect(page.getByText(docTitle)).toBeVisible()

    await page.goto(`/projects/${project.id}/requirements/analyses/${analysis.id}`)
    await expect(page.getByText('需求分析').first()).toBeVisible()
    await expect(page.getByText('测试点审核')).toBeVisible()
    await expect(page.getByText('用例草稿审核')).toBeVisible()
    await expect(page.getByText('用例追溯')).toBeVisible()

    await page.goto(`/projects/${project.id}/assets/testcases`)
    await expect(page.getByText(directCaseTitle)).toBeVisible()

    await page.goto(`/projects/${project.id}/runs`)
    await expect(page.locator('div').filter({ hasText: /^运行记录$/ })).toBeVisible()
    await expect(page.getByRole('button', { name: run.id })).toBeVisible()

    await page.goto(`/projects/${project.id}/defects`)
    await expect(page.getByText('缺陷管理').first()).toBeVisible()
    await expect(page.getByText(defectTitle)).toBeVisible()

    await page.goto(`/projects/${project.id}/knowledge/retrospectives`)
    await expect(page.getByText('复盘中心')).toBeVisible()
    await expect(page.getByText(retrospectiveTitle).first()).toBeVisible()
  })
})
