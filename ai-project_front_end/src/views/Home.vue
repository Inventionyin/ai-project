<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import DashboardHeader from '@/components/DashboardHeader.vue'
import StatsCard from '@/components/StatsCard.vue'
import ProjectCard from '@/components/ProjectCard.vue'
import CreateProjectModal from '@/components/CreateProjectModal.vue'
import UserProfile from '@/components/UserProfile.vue'
import EditProjectModal from '@/components/EditProjectModal.vue'
import DeleteConfirmationModal from '@/components/DeleteConfirmationModal.vue'

const router = useRouter()
const isCreateModalOpen = ref(false)
const isEditModalOpen = ref(false)
const isDeleteModalOpen = ref(false)
const isPermissionDeniedModalOpen = ref(false)
const permissionDeniedModalMessage = ref('')
const selectedProject = ref<HomeProject | null>(null)
const isMyProjectsFilterActive = ref(false)
const currentUserName = ref('张三')
const currentUserId = ref('')
const isCreatingProject = ref(false)
const isUpdatingProject = ref(false)

const openProjectPermissionDeniedModal = () => {
  permissionDeniedModalMessage.value = '只有 创建人/管理员 能修改这个项目'
  isPermissionDeniedModalOpen.value = true
}

const closeProjectPermissionDeniedModal = () => {
  isPermissionDeniedModalOpen.value = false
  permissionDeniedModalMessage.value = ''
}

const isProjectPermissionDenied = (response: Response, payload: ApiResponse<unknown>) => {
  if (response.status === 403) return true
  return Number(payload.code) === 40301
}

const handleEditClick = (project: HomeProject) => {
  selectedProject.value = project
  isEditModalOpen.value = true
}

const handleDeleteClick = (project: HomeProject) => {
  selectedProject.value = project
  isDeleteModalOpen.value = true
}

const handleSaveProject = async (data: { name: string; description: string }) => {
  if (!selectedProject.value || isUpdatingProject.value) return
  isUpdatingProject.value = true
  try {
    const authorization = resolveAuthHeader()
    const projectId = selectedProject.value.id
    const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${projectId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authorization
      },
      body: JSON.stringify({
        name: data.name.trim(),
        description: data.description.trim() || undefined
      })
    })
    const payload = await response.json() as ApiResponse<ProjectData>
    if (!response.ok || payload.code !== 0 || !payload.data) {
      if (isProjectPermissionDenied(response, payload)) {
        isEditModalOpen.value = false
        selectedProject.value = null
        openProjectPermissionDeniedModal()
        return
      }
      throw new Error(payload.message || '编辑项目失败，请稍后重试')
    }
    const index = projects.value.findIndex(p => p.id === projectId)
    if (index !== -1) {
      projects.value[index] = toHomeProject(payload.data)
    }
    isEditModalOpen.value = false
    selectedProject.value = null
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '编辑项目失败，请稍后重试'
    window.alert(errorMessage)
  } finally {
    isUpdatingProject.value = false
  }
}

const confirmDeleteProject = async () => {
  if (!selectedProject.value) {
    isDeleteModalOpen.value = false
    return
  }

  const projectId = selectedProject.value.id
  try {
    const authorization = resolveAuthHeader()
    const response = await fetch(`${resolveApiBaseUrl()}/api/projects/${projectId}`, {
      method: 'DELETE',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<null>
    if (!response.ok || payload.code !== 0) {
      if (isProjectPermissionDenied(response, payload)) {
        isDeleteModalOpen.value = false
        selectedProject.value = null
        openProjectPermissionDeniedModal()
        return
      }
      throw new Error(payload.message || '删除项目失败，请稍后重试')
    }

    projects.value = projects.value.filter(p => p.id !== projectId)
    try {
      await loadProjects(authorization)
      await loadHomeStats(authorization)
    } catch {}
    isDeleteModalOpen.value = false
    selectedProject.value = null
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '删除项目失败，请稍后重试'
    window.alert(errorMessage)
  }
}

const homeStats = ref<HomeStatsData>({
  projectTotal: 0,
  testcaseTotal: 0,
  todayRunTotal: 0,
  todayPassRate: 0
})

const formatPassRate = (value: number) => {
  const normalized = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0
  return Number.isInteger(normalized) ? `${normalized}%` : `${normalized.toFixed(1)}%`
}

const stats = computed(() => [
  { 
    label: '项目总数', 
    value: homeStats.value.projectTotal,
    iconColor: 'bg-indigo-50',
    iconPath: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z'
  },
  { 
    label: '用例总数', 
    value: homeStats.value.testcaseTotal,
    iconColor: 'bg-blue-50',
    iconPath: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
  },
  { 
    label: '今日执行', 
    value: `${homeStats.value.todayRunTotal} 次`,
    iconColor: 'bg-green-50',
    iconPath: 'M13 10V3L4 14h7v7l9-11h-7z'
  },
  { 
    label: '平均通过率', 
    value: formatPassRate(homeStats.value.todayPassRate),
    iconColor: 'bg-orange-50',
    iconPath: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
  }
])

const projects = ref<HomeProject[]>([])

const searchQuery = ref('')

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

type CurrentUserData = {
  userId: string
  username?: string | null
  name?: string | null
}

type ProjectData = {
  id: string
  name: string
  description?: string | null
  ownerId: string
  memberCount: number
  caseCount?: number
  passRate?: number | null
  createdAt: number
}

type ProjectListItem = {
  id: string
  name: string
  description?: string | null
  ownerId: string
  memberCount: number
  caseCount: number
  passRate?: number | null
  createdAt: number
}

type HomeStatsData = {
  projectTotal: number
  testcaseTotal: number
  todayRunTotal: number
  todayPassRate: number
}

type HomeProject = {
  id: string
  title: string
  description: string
  tags: Array<{ text: string; bg: string; color: string }>
  stats: Array<{ label: string; value: string | number; color: string }>
  iconColor: string
  owner: string
  ownerId: string
  date: string
}

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

const parseCreatedAt = (value: number) => {
  const timestamp = value > 1_000_000_000_000 ? value : value * 1000
  return new Date(timestamp).toLocaleString()
}

const resolveOwnerDisplayName = (ownerId: string) => {
  if (ownerId === currentUserId.value) {
    return currentUserName.value
  }
  return ownerId.slice(0, 8)
}

const toHomeProject = (project: ProjectListItem | ProjectData): HomeProject => ({
  id: project.id,
  title: project.name,
  description: ('description' in project ? project.description : undefined) || '暂无描述',
  tags: [
    { text: '已创建', bg: 'bg-indigo-50', color: 'text-indigo-600' },
    { text: 'P1', bg: 'bg-indigo-50', color: 'text-indigo-600' }
  ],
  stats: [
    { label: '用例数', value: project.caseCount ?? 0, color: 'text-gray-900' },
    { label: '通过率', value: typeof project.passRate === 'number' ? formatPassRate(project.passRate) : '-', color: typeof project.passRate === 'number' ? 'text-gray-900' : 'text-gray-400' },
    { label: '成员数', value: project.memberCount, color: 'text-gray-900' }
  ],
  iconColor: 'bg-indigo-600',
  owner: resolveOwnerDisplayName(project.ownerId),
  ownerId: project.ownerId,
  date: parseCreatedAt(project.createdAt)
})

const loadCurrentUser = async (authorization: string) => {
  const meResponse = await fetch(`${resolveApiBaseUrl()}/api/auth/me`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const mePayload = await meResponse.json() as ApiResponse<CurrentUserData>
  if (!meResponse.ok || mePayload.code !== 0 || !mePayload.data?.userId) {
    throw new Error(mePayload.message || '获取当前用户信息失败')
  }
  currentUserId.value = mePayload.data.userId
  currentUserName.value = mePayload.data.name || mePayload.data.username || currentUserName.value
  return mePayload.data
}

const loadProjects = async (authorization: string) => {
  const response = await fetch(`${resolveApiBaseUrl()}/api/projects?page=1&pageSize=200`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const payload = await response.json() as ApiResponse<PageData<ProjectListItem>>
  if (!response.ok || payload.code !== 0 || !payload.data) {
    throw new Error(payload.message || '获取项目列表失败，请稍后重试')
  }
  projects.value = payload.data.items.map(toHomeProject)
}

const loadHomeStats = async (authorization: string) => {
  const response = await fetch(`${resolveApiBaseUrl()}/api/projects/home-stats`, {
    method: 'GET',
    headers: {
      Authorization: authorization
    }
  })
  const payload = await response.json() as ApiResponse<HomeStatsData>
  if (!response.ok || payload.code !== 0 || !payload.data) {
    throw new Error(payload.message || '获取首页统计失败，请稍后重试')
  }
  homeStats.value = payload.data
}

const filteredProjects = computed(() => {
  return projects.value.filter(project => {
    // Filter by search query
    const matchesSearch = project.title.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
                          project.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    
    // Filter by owner if "My Projects" is active
    const matchesOwner = isMyProjectsFilterActive.value
      ? (currentUserId.value ? project.ownerId === currentUserId.value : false)
      : true
    
    return matchesSearch && matchesOwner
  })
})

const handleCreateProject = async (data: { name: string; description: string }) => {
  if (isCreatingProject.value) return

  isCreatingProject.value = true
  try {
    const authorization = resolveAuthHeader()
    const meData = await loadCurrentUser(authorization)

    const response = await fetch(`${resolveApiBaseUrl()}/api/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authorization
      },
      body: JSON.stringify({
        name: data.name.trim(),
        description: data.description.trim() || undefined,
        ownerId: meData.userId
      })
    })
    const payload = await response.json() as ApiResponse<ProjectData>

    if (!response.ok || payload.code !== 0 || !payload.data) {
      throw new Error(payload.message || '创建项目失败，请稍后重试')
    }

    projects.value.unshift(toHomeProject(payload.data))
    try {
      await loadProjects(authorization)
      await loadHomeStats(authorization)
    } catch {}
    isCreateModalOpen.value = false
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '创建项目失败，请稍后重试'
    window.alert(errorMessage)
  } finally {
    isCreatingProject.value = false
  }
}

const navigateToDashboard = (projectId: string) => {
  router.push(`/projects/${projectId}/dashboard`)
}

onMounted(() => {
  const initializeHome = async () => {
    try {
      const authorization = resolveAuthHeader()
      await loadCurrentUser(authorization)
      await loadProjects(authorization)
      await loadHomeStats(authorization)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '获取项目列表失败，请稍后重试'
      window.alert(errorMessage)
    }
  }
  void initializeHome()
})
</script>

<template>
  <div class="min-h-screen flex flex-col font-sans bg-gray-50">
    <!-- Top Section: Header -->
    <div class="bg-white py-6 px-6 border-b border-gray-200">
      <div class="max-w-7xl mx-auto flex justify-between items-center">
        <DashboardHeader 
          title="AI 测试平台" 
          subtitle="智能化测试资产管理与执行编排"
          @create="isCreateModalOpen = true"
        />
        <div class="flex items-center gap-4">
          <button 
            @click="isCreateModalOpen = true"
            class="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 px-5 rounded-[10px] flex items-center gap-2 transition-colors shadow-sm text-sm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
            </svg>
            新建项目
          </button>
          <UserProfile />
        </div>
      </div>
    </div>

    <!-- Bottom Section: Stats & Projects -->
    <div class="flex-1 bg-gray-100 px-6 py-8">
      <div class="max-w-7xl mx-auto space-y-8">
        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatsCard 
            v-for="(stat, idx) in stats" 
            :key="idx"
            :label="stat.label"
            :value="stat.value"
            :icon-bg-color="stat.iconColor"
          >
            <template #icon>
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                class="w-5 h-5 text-indigo-600" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="stat.iconPath" />
              </svg>
            </template>
          </StatsCard>
        </div>

        <!-- Projects Section -->
        <div class="space-y-6">
        <div class="flex flex-col sm:flex-row items-center gap-4">
          <!-- Search Bar -->
          <div class="relative w-full sm:w-80">
            <input 
              v-model="searchQuery"
              type="text" 
              placeholder="搜索项目名..." 
              class="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-[10px] text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-shadow"
            />
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              class="h-4 w-4 text-gray-400 absolute left-3 top-2.5" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <!-- "My Projects" Button/Label -->
          <div 
            @click="isMyProjectsFilterActive = !isMyProjectsFilterActive"
            class="border font-medium py-2 px-4 rounded-[10px] shadow-sm flex items-center gap-2 text-sm cursor-pointer transition-colors select-none"
            :class="[
              isMyProjectsFilterActive 
                ? 'bg-indigo-600 border-indigo-600 text-white hover:bg-indigo-700' 
                : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
            ]"
          >
            我的项目
          </div>
        </div>

        <!-- Projects Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <ProjectCard 
            v-for="project in filteredProjects" 
            :key="project.id"
            :project="project"
            @click="navigateToDashboard(project.id)"
            @edit="handleEditClick"
            @delete="handleDeleteClick"
          />
        </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CreateProjectModal 
      :is-open="isCreateModalOpen" 
      @close="isCreateModalOpen = false" 
      @create="handleCreateProject" 
    />

    <EditProjectModal
      :is-open="isEditModalOpen"
      :project="selectedProject"
      :is-saving="isUpdatingProject"
      @close="isEditModalOpen = false"
      @save="handleSaveProject"
    />

    <DeleteConfirmationModal
      :is-open="isDeleteModalOpen"
      :project-name="selectedProject ? selectedProject.title : ''"
      @close="isDeleteModalOpen = false"
      @confirm="confirmDeleteProject"
    />

    <div v-if="isPermissionDeniedModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" @click.self="closeProjectPermissionDeniedModal">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-sm mx-4">
        <div class="p-6">
          <div class="text-center">
            <h3 class="text-lg font-medium text-gray-900">提示</h3>
            <p class="mt-3 text-sm text-gray-600">{{ permissionDeniedModalMessage }}</p>
          </div>
        </div>
        <div class="bg-gray-50 px-4 py-3 sm:px-6 flex justify-center">
          <button @click="closeProjectPermissionDeniedModal" type="button" class="inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">我知道了</button>
        </div>
      </div>
    </div>
  </div>
</template>
