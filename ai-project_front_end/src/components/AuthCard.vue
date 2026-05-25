<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'login-success'): void
}>()

// Login State
const loginUsername = ref('')
const loginPassword = ref('')
const showLoginPassword = ref(false)
const loginPasswordError = ref('')
const loginError = ref('')
const isLoggingIn = ref(false)

const resetLoginForm = () => {
  loginUsername.value = ''
  loginPassword.value = ''
  showLoginPassword.value = false
  loginPasswordError.value = ''
  loginError.value = ''
}

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const handleLogin = () => {
  if (!loginUsername.value || !loginPassword.value || isLoggingIn.value) return

  const login = async () => {
    isLoggingIn.value = true
    loginError.value = ''
    try {
      const response = await fetch(`${resolveApiBaseUrl()}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: loginUsername.value.trim(),
          password: loginPassword.value
        })
      })
      const payload = await response.json() as {
        code?: number
        message?: string
        data?: {
          accessToken?: string
          expiresIn?: number
        }
      }

      if (!response.ok || payload.code !== 0 || !payload.data?.accessToken || !payload.data.expiresIn) {
        loginError.value = payload.message || '登录失败，请检查用户名或密码'
        return
      }

      const expiresAt = Date.now() + payload.data.expiresIn * 1000
      localStorage.setItem('accessToken', payload.data.accessToken)
      localStorage.setItem('accessTokenExpiresAt', String(expiresAt))
      localStorage.setItem('loginUsername', loginUsername.value.trim())
      emit('login-success')
    } catch {
      loginError.value = '网络异常，请确认后端服务已启动'
    } finally {
      isLoggingIn.value = false
    }
  }

  void login()
}

const toggleLoginPassword = () => {
  showLoginPassword.value = !showLoginPassword.value
}

resetLoginForm()
</script>

<template>
  <div class="flex flex-col items-center gap-8 w-full max-w-[448px]">
    <!-- Header Section -->
    <div class="flex flex-col items-center gap-4">
      <!-- Logo -->
      <div class="w-14 h-14 bg-brand-blue rounded-2xl shadow-[0px_4px_6px_-4px_rgba(21,93,252,0.3),0px_10px_15px_-3px_rgba(21,93,252,0.3)] flex items-center justify-center relative overflow-hidden">
         <!-- Simple Logo Shape Placeholder -->
         <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="9.33" y="4.67" width="4.67" height="4.67" fill="white" fill-opacity="0.8"/>
            <rect x="14" y="9.33" width="4.67" height="4.67" fill="white" fill-opacity="0.8"/>
            <rect x="4.67" y="9.33" width="4.67" height="4.67" fill="white" fill-opacity="0.8"/>
            <path d="M14 14L23 23" stroke="white" stroke-width="2.33" stroke-linecap="round"/>
         </svg>
      </div>
      
      <!-- Text -->
      <div class="text-center">
        <h1 class="text-2xl font-semibold text-white mb-2">WeiTesting</h1>
        <p class="text-brand-text-gray text-sm">智能化测试资产管理与执行编排</p>
      </div>
    </div>

    <!-- Main Card -->
    <div class="w-full bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl shadow-2xl p-8 flex flex-col gap-6">
      
      <!-- Tab Switcher -->
      <div class="flex p-1 bg-white/5 rounded-xl">
        <div class="flex-1 py-1.5 text-center text-sm font-medium rounded-lg bg-brand-blue text-white shadow-sm">
          账号登录
        </div>
      </div>

      <!-- Login Form -->
      <form class="flex flex-col gap-4" @submit.prevent="handleLogin">
        <!-- Email Input -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#CAD5E2]">邮箱</label>
          <div class="relative group">
            <input 
              v-model="loginUsername"
              type="email"
              autocomplete="username"
              class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
              placeholder="请输入邮箱"
              @input="loginError = ''"
            />
          </div>
        </div>

        <!-- Password Input -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#CAD5E2]">密码</label>
          <div class="relative group">
            <input 
              v-model="loginPassword"
              :type="showLoginPassword ? 'text' : 'password'"
              autocomplete="new-password"
              class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all pr-10"
              placeholder="请输入密码"
              @input="loginPasswordError = ''"
            />
            <div v-if="loginPasswordError" class="text-red-500 text-xs mt-1">{{ loginPasswordError }}</div>
            <button 
              type="button"
              @click="toggleLoginPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
            >
              <svg v-if="!showLoginPassword" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 3l18 18" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Login Button -->
        <button
          :disabled="isLoggingIn"
          class="w-full bg-brand-blue hover:bg-blue-600 text-white text-sm font-medium py-2.5 rounded-lg transition-colors shadow-lg shadow-blue-500/20 mt-2 disabled:cursor-not-allowed disabled:opacity-80"
        >
          {{ isLoggingIn ? '登录中...' : '登 录' }}
        </button>

        <div v-if="loginError" class="w-full bg-[#3B1219] border border-[#5D1820] rounded-lg p-3 text-[#FB2C36] text-sm text-center">
          {{ loginError }}
        </div>

      </form>
    </div>

    <!-- Footer -->
    <div class="text-center">
      <p class="text-xs text-[#45556C]">© {{ new Date().getFullYear() }} WeiTesting · 企业内部测试工具</p>
    </div>
  </div>
</template>

<style scoped>
/* Custom Scrollbar for inputs if needed */
input::-ms-reveal,
input::-ms-clear {
  display: none;
}
</style>
