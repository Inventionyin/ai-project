<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { LogOut } from 'lucide-vue-next'

type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
}

type CurrentUserData = {
  userId: string
  email?: string | null
  phone?: string | null
  username?: string | null
  name?: string | null
  roles?: string[]
}

const isMenuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)
const router = useRouter()
const isLoading = ref(false)
const userData = ref<CurrentUserData | null>(null)

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const resolveAuthorization = () => {
  const accessToken = localStorage.getItem('accessToken')
  return accessToken ? `Bearer ${accessToken}` : ''
}

const userInitials = computed(() => {
  const source = userData.value?.name || userData.value?.username || 'U'
  return source.slice(0, 2).toUpperCase()
})

const userDisplayName = computed(() => {
  return userData.value?.name || userData.value?.username || '未命名用户'
})

const userDisplayPhone = computed(() => {
  return userData.value?.phone || userData.value?.email || '-'
})

const userDisplayRole = computed(() => {
  const firstRole = userData.value?.roles?.[0]
  return firstRole || '普通成员'
})

const loadCurrentUser = async () => {
  if (isLoading.value) return
  const authorization = resolveAuthorization()
  if (!authorization) {
    userData.value = null
    return
  }
  isLoading.value = true
  try {
    const response = await fetch(`${resolveApiBaseUrl()}/api/auth/me`, {
      method: 'GET',
      headers: {
        Authorization: authorization
      }
    })
    const payload = await response.json() as ApiResponse<CurrentUserData>
    if (!response.ok || payload.code !== 0 || !payload.data?.userId) {
      throw new Error(payload.message || '获取用户信息失败')
    }
    userData.value = payload.data
  } catch {
    userData.value = null
  } finally {
    isLoading.value = false
  }
}

const handleAvatarClick = async () => {
  const nextState = !isMenuOpen.value
  isMenuOpen.value = nextState
  if (!nextState) return
  await loadCurrentUser()
}

const handleLogout = async () => {
  const authorization = resolveAuthorization()
  if (authorization) {
    try {
      await fetch(`${resolveApiBaseUrl()}/api/auth/logout`, {
        method: 'POST',
        headers: {
          Authorization: authorization
        }
      })
    } catch {}
  }
  localStorage.removeItem('accessToken')
  localStorage.removeItem('accessTokenExpiresAt')
  isMenuOpen.value = false
  await router.push('/login')
}

const onWindowClick = (e: MouseEvent) => {
  const el = menuRef.value
  if (!el) return
  if (!el.contains(e.target as Node)) {
    isMenuOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('click', onWindowClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick)
})
</script>

<template>
  <div ref="menuRef" class="relative">
    <button @click="handleAvatarClick" class="w-7 h-7 rounded-full bg-brand-blue flex items-center justify-center">
      <span class="text-xs font-semibold text-white leading-4">{{ userInitials }}</span>
    </button>

    <div
      v-if="isMenuOpen"
      class="absolute right-0 top-full mt-2 w-48 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-20"
    >
      <div class="py-1">
        <div class="px-4 py-3 min-h-[80px]">
          <template v-if="isLoading">
            <p class="text-sm text-gray-500">正在加载用户信息...</p>
          </template>
          <template v-else>
            <p class="text-sm font-semibold text-gray-900">{{ userDisplayName }}</p>
            <p class="text-sm text-gray-500">{{ userDisplayPhone }}</p>
            <p class="text-xs mt-1 px-2 py-0.5 inline-flex leading-4 bg-blue-100 text-blue-800 rounded-full">{{ userDisplayRole }}</p>
          </template>
        </div>
        <div class="border-t border-gray-100"></div>
        <button type="button" @click="handleLogout" class="w-full flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
          <LogOut class="mr-3 h-5 w-5 text-gray-400" />
          <span>退出登录</span>
        </button>
      </div>
    </div>
  </div>
</template>
