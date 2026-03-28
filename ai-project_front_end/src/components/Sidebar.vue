<script setup lang="ts">
import { 
  LayoutDashboard, 
  Briefcase, 
  PlayCircle, 
  FileText, 
  Bot, 
  ChevronDown,
  FileCode,
  Layers,
  Database,
  Server,
  History,
  Settings,
  Users,
  Plug,
  Activity
} from 'lucide-vue-next'
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const props = defineProps<{
  projects: string[]
  selectedProject: string
  isCollapsed: boolean // New prop to control collapsed state
}>()

const emit = defineEmits<{
  (e: 'selectProject', name: string): void
}>()

const isProjectListOpen = ref(false)

const navItems = [
  { 
    name: '仪表盘', 
    icon: LayoutDashboard, 
    path: '/dashboard/overview'
  },
  {
    name: '资产中心',
    icon: Briefcase,
    path: '/dashboard/assets',
    children: [
      { name: '用例管理', icon: FileCode, path: '/figma/untitled-34-158' },
      { name: '测试套件', icon: Layers, path: '/figma/untitled-47-1415' },
      { name: '接口集合', icon: Database, path: '/dashboard/assets' },
      { name: '测试数据', icon: Server, path: '/dashboard/assets' }
    ]
  },
  {
    name: '执行中心',
    icon: PlayCircle,
    children: [
      { name: '运行记录', icon: History, path: '/dashboard/overview' },
      { name: 'Worker 管理', icon: Server, path: '/dashboard/overview' }
    ]
  },
  { name: '报告中心', icon: FileText, path: '/dashboard/overview' },
  { name: 'AI 助手', icon: Bot, path: '/dashboard/overview' }
]

const settingItems = [
  { name: '环境管理', icon: Settings, path: '/dashboard/settings/env' },
  { name: '成员权限', icon: Users, path: '/dashboard/settings/members' },
  { name: '集成配置', icon: Plug, path: '/dashboard/settings/integration' },
  { name: '审计日志', icon: Activity, path: '/dashboard/settings/audit' }
]

const navigateTo = (path?: string) => {
  if (path) {
    router.push(path)
  }
}

const isActive = (path?: string) => (path ? route.path.startsWith(path) : false)
const isItemActive = (item: { path?: string; children?: { path?: string }[] }) =>
  isActive(item.path) || (item.children?.some((child) => isActive(child.path)) ?? false)

const selectProject = (name: string) => {
  emit('selectProject', name)
  isProjectListOpen.value = false
}

// Use a computed property to simulate the collapsed state for preview
const isCollapsedForPreview = computed(() => true);

</script>

<template>
  <aside 
    class="h-screen bg-gray-50 border-r border-gray-200 flex flex-col fixed left-0 top-0 overflow-y-auto z-20 transition-width duration-300"
    :class="isCollapsedForPreview ? 'w-20' : 'w-64'"
  >
    <!-- Header -->
    <div class="p-4 border-b border-gray-100 cursor-pointer" @click="router.push('/home')">
      <div class="flex items-center gap-2 mb-1" :class="{'justify-center': isCollapsedForPreview}">
        <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <span class="text-white font-bold text-lg">AI</span>
        </div>
        <span v-if="!isCollapsedForPreview" class="font-bold text-gray-800 text-lg">AI 测试平台</span>
      </div>
      <div v-if="!isCollapsedForPreview" class="text-xs text-gray-500 ml-10">v1.0.0</div>
    </div>

    <!-- Project Selection -->
    <div class="p-4 border-b border-gray-100">
      <div class="space-y-2">
        <div
          class="flex items-center justify-between gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors hover:bg-gray-100"
          @click="isProjectListOpen = !isProjectListOpen"
        >
          <div class="flex items-center gap-2 min-w-0">
            <div class="w-2 h-2 rounded-full bg-blue-600 flex-shrink-0"></div>
            <span v-if="!isCollapsedForPreview" class="text-sm font-medium text-gray-900 truncate">{{ props.selectedProject }}</span>
          </div>
          <ChevronDown
            v-if="!isCollapsedForPreview"
            class="w-4 h-4 text-gray-400 transition-transform"
            :class="isProjectListOpen ? 'rotate-180' : ''"
          />
        </div>

        <div v-if="isProjectListOpen && !isCollapsedForPreview" class="space-y-1">
          <div
            v-for="projectName in props.projects"
            :key="projectName"
            class="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors"
            :class="
              projectName === props.selectedProject ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-100 text-gray-600'
            "
            @click.stop="selectProject(projectName)"
          >
            <div
              class="w-2 h-2 rounded-full"
              :class="projectName === props.selectedProject ? 'bg-blue-600' : 'bg-gray-400'"
            ></div>
            <span class="text-sm font-medium">{{ projectName }}</span>
          </div>
        </div>
        <div v-if="!isCollapsedForPreview" class="px-3 py-2 text-sm text-gray-500 hover:text-blue-600 cursor-pointer flex items-center gap-2" @click="router.push('/home')">
          <span>+ 所有项目</span>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
      <div v-for="item in navItems" :key="item.name">
        <div 
          class="flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1"
          :class="[
            isItemActive(item) ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50',
            isCollapsedForPreview ? 'justify-center' : ''
          ]"
          @click="navigateTo(item.path)"
        >
          <div class="flex items-center gap-3">
            <component :is="item.icon" class="w-5 h-5 flex-shrink-0" />
            <span v-if="!isCollapsedForPreview" class="text-sm font-medium">{{ item.name }}</span>
          </div>
          <ChevronDown v-if="item.children && !isCollapsedForPreview" class="w-4 h-4 text-gray-400" />
        </div>
        
        <!-- Submenu -->
        <div v-if="item.children && !isCollapsedForPreview" class="ml-4 pl-4 border-l border-gray-200 space-y-1 mb-2">
          <div 
             v-for="child in item.children"
             :key="child.name"
             class="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors text-sm"
             :class="isActive(child.path) ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-500 hover:text-gray-900'"
             @click.stop="navigateTo(child.path)"
          >
             <component :is="child.icon" class="w-4 h-4 flex-shrink-0" />
             <span>{{ child.name }}</span>
          </div>
        </div>
      </div>

      <!-- Settings Section -->
      <div class="pt-4 mt-4 border-t border-gray-100">
        <div v-if="!isCollapsedForPreview" class="px-3 mb-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">设置</div>
        <div v-for="item in settingItems" :key="item.name">
          <div 
            class="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1 text-gray-600 hover:bg-gray-50"
            :class="[
              isActive(item.path) ? 'bg-blue-50 text-blue-700' : '',
              isCollapsedForPreview ? 'justify-center' : ''
            ]"
            @click="navigateTo(item.path)"
          >
            <component :is="item.icon" class="w-5 h-5 flex-shrink-0" />
            <span v-if="!isCollapsedForPreview" class="text-sm font-medium">{{ item.name }}</span>
          </div>
        </div>
      </div>
    </nav>

    <!-- User Profile -->
    <div class="p-4 border-t border-gray-200" :class="{'p-2': isCollapsedForPreview}">
      <div class="flex items-center gap-3" :class="{'justify-center': isCollapsedForPreview}">
        <div class="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm flex-shrink-0">
          ZS
        </div>
        <div v-if="!isCollapsedForPreview" class="flex flex-col">
          <span class="text-sm font-medium text-gray-900">张三</span>
          <span class="text-xs text-gray-500">测试工程师</span>
        </div>
      </div>
    </div>
  </aside>
</template>
