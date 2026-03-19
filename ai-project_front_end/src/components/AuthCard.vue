<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  initialTab?: 'login' | 'register'
}>()

const emit = defineEmits<{
  (e: 'login-success'): void
  (e: 'register-success'): void
}>()

const activeTab = ref<'login' | 'register'>(props.initialTab || 'login')

// Login State
const loginUsername = ref('')
const loginPassword = ref('')
const showLoginPassword = ref(false)
const loginPasswordError = ref('')
const loginError = ref('')
const isLoggingIn = ref(false)

// Register State
const registerUsername = ref('')
const registerPhone = ref('')
const registerVerifyCode = ref('')
const registerPassword = ref('')
const registerConfirmPassword = ref('')
const showRegisterPassword = ref(false)
const showRegisterConfirmPassword = ref(false)
const registerUsernameError = ref('')
const phoneError = ref('')
const registerVerifyCodeError = ref('')
const registerPasswordError = ref('')
const registerConfirmPasswordError = ref('')
const registerError = ref('')

// Timer State
const countdown = ref(60)
const isCountingDown = ref(false)

const isRegistering = ref(false)
let countdownTimer: number | null = null

const stopTimer = () => {
  if (countdownTimer !== null) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  isCountingDown.value = false
  countdown.value = 60
}

const resetLoginForm = () => {
  loginUsername.value = ''
  loginPassword.value = ''
  showLoginPassword.value = false
  loginPasswordError.value = ''
  loginError.value = ''
}

const resetRegisterForm = () => {
  registerUsername.value = ''
  registerPhone.value = ''
  registerVerifyCode.value = ''
  registerPassword.value = ''
  registerConfirmPassword.value = ''
  showRegisterPassword.value = false
  showRegisterConfirmPassword.value = false
  registerUsernameError.value = ''
  phoneError.value = ''
  registerVerifyCodeError.value = ''
  registerPasswordError.value = ''
  registerConfirmPasswordError.value = ''
  registerError.value = ''
  stopTimer()
}

const resetAllForms = () => {
  resetLoginForm()
  resetRegisterForm()
}

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

// Handle register function
const handleRegister = () => {
  if (isRegistering.value) return

  let hasError = false
  registerUsernameError.value = ''
  phoneError.value = ''
  registerVerifyCodeError.value = ''
  registerPasswordError.value = ''
  registerConfirmPasswordError.value = ''
  registerError.value = ''

  const normalizedUsername = registerUsername.value.trim()
  const normalizedPhone = registerPhone.value.trim()
  const normalizedCaptcha = registerVerifyCode.value.trim()

  if (!normalizedUsername) {
    registerUsernameError.value = '请输入用户名'
    hasError = true
  }
  if (!normalizedPhone) {
    phoneError.value = '请输入手机号'
    hasError = true
  } else if (!/^1[3-9]\d{9}$/.test(normalizedPhone)) {
    phoneError.value = '请输入正确的手机号'
    hasError = true
  }
  if (!normalizedCaptcha) {
    registerVerifyCodeError.value = '请输入验证码'
    hasError = true
  }
  if (!registerPassword.value) {
    registerPasswordError.value = '请设置密码'
    hasError = true
  } else if (registerPassword.value.length < 8) {
    registerPasswordError.value = '密码至少 8 位'
    hasError = true
  } else if (!/[A-Za-z]/.test(registerPassword.value) || !/\d/.test(registerPassword.value)) {
    registerPasswordError.value = '密码需包含字母和数字'
    hasError = true
  }
  if (!registerConfirmPassword.value) {
    registerConfirmPasswordError.value = '请再次输入密码'
    hasError = true
  } else if (registerPassword.value !== registerConfirmPassword.value) {
    registerConfirmPasswordError.value = '两次输入的密码不一致'
    hasError = true
  }

  if (hasError) return

  const register = async () => {
    isRegistering.value = true
    try {
      const response = await fetch(`${resolveApiBaseUrl()}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          phone: normalizedPhone,
          username: normalizedUsername,
          password: registerPassword.value,
          confirmPassword: registerConfirmPassword.value,
          captcha: normalizedCaptcha
        })
      })
      const payload = await response.json() as {
        code?: number
        message?: string
      }

      if (!response.ok || payload.code !== 0) {
        registerError.value = payload.message || '注册失败，请稍后重试'
        return
      }

      activeTab.value = 'login'

      emit('register-success')
    } catch {
      registerError.value = '网络异常，请确认后端服务已启动'
    } finally {
      isRegistering.value = false
    }
  }

  void register()
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

const startTimer = () => {
  if (isCountingDown.value) return

  // Validate phone number
  if (!/^1[3-9]\d{9}$/.test(registerPhone.value.trim())) {
    phoneError.value = '请输入正确的手机号'
    return
  }
  
  phoneError.value = ''
  registerError.value = ''
  isCountingDown.value = true
  countdown.value = 60
  countdownTimer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      stopTimer()
    }
  }, 1000)
}

watch(activeTab, () => {
  resetAllForms()
})

watch(() => props.initialTab, (newVal) => {
  if (!newVal) return
  activeTab.value = newVal
  resetAllForms()
})

resetAllForms()

onBeforeUnmount(() => {
  stopTimer()
})

const toggleLoginPassword = () => {
  showLoginPassword.value = !showLoginPassword.value
}

const toggleRegisterPassword = () => {
  showRegisterPassword.value = !showRegisterPassword.value
}

const toggleRegisterConfirmPassword = () => {
  showRegisterConfirmPassword.value = !showRegisterConfirmPassword.value
}
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
        <h1 class="text-2xl font-semibold text-white mb-2">AI 测试平台</h1>
        <p class="text-brand-text-gray text-sm">智能化测试资产管理与执行编排</p>
      </div>
    </div>

    <!-- Main Card -->
    <div class="w-full bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl shadow-2xl p-8 flex flex-col gap-6">
      
      <!-- Tab Switcher -->
      <div class="flex p-1 bg-white/5 rounded-xl">
        <button 
          @click="activeTab = 'login'"
          class="flex-1 py-1.5 text-sm font-medium rounded-lg transition-all duration-200"
          :class="activeTab === 'login' ? 'bg-brand-blue text-white shadow-sm' : 'text-brand-text-gray hover:text-white'"
        >
          账号登录
        </button>
        <button 
          @click="activeTab = 'register'"
          class="flex-1 py-1.5 text-sm font-medium rounded-lg transition-all duration-200"
          :class="activeTab === 'register' ? 'bg-brand-blue text-white shadow-sm' : 'text-brand-text-gray hover:text-white'"
        >
          注册账号
        </button>
      </div>

      <!-- Login Form -->
      <form v-if="activeTab === 'login'" class="flex flex-col gap-4" @submit.prevent="handleLogin">
        <!-- Email Input -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#CAD5E2]">用户名</label>
          <div class="relative group">
            <input 
              v-model="loginUsername"
              type="text" 
              autocomplete="off"
              class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
              placeholder="请输入用户名"
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

      <!-- Register Form -->
      <form v-else class="flex flex-col gap-4" @submit.prevent="handleRegister">
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#CAD5E2]">用户名</label>
          <div class="relative group">
            <div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-white transition-colors">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M20 21V19C20 17.3431 18.6569 16 17 16H7C5.34315 16 4 17.3431 4 19V21" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 12C14.2091 12 16 10.2091 16 8C16 5.79086 14.2091 4 12 4C9.79086 4 8 5.79086 8 8C8 10.2091 9.79086 12 12 12Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <input
              v-model="registerUsername"
              type="text"
              autocomplete="off"
              class="w-full bg-white/10 border border-white/20 rounded-lg pl-10 pr-3 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
              placeholder="请输入用户名"
            />
          </div>
        </div>

        <!-- Phone Input -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#CAD5E2]">手机号</label>
          <div class="relative group">
            <div class="absolute left-3 top-1/2 -translate-y-1/2 group-focus-within:text-white transition-colors" :class="phoneError ? 'text-[#FB2C36]' : 'text-gray-400'">
              <!-- Phone Icon -->
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10.5 1.5H8.25C7.00736 1.5 6 2.50736 6 3.75V20.25C6 21.4926 7.00736 22.5 8.25 22.5H15.75C16.9926 22.5 18 21.4926 18 20.25V3.75C18 2.50736 16.9926 1.5 15.75 1.5H13.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 18.75H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <input 
              v-model="registerPhone"
              type="tel" 
              autocomplete="off"
              class="w-full bg-white/10 border rounded-lg pl-10 pr-3 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none transition-all"
              :class="phoneError ? 'border-[#FB2C36] focus:border-[#FB2C36] focus:ring-1 focus:ring-[#FB2C36]' : 'border-white/20 focus:border-brand-blue focus:ring-1 focus:ring-brand-blue'"
              placeholder="请输入手机号"
              @input="phoneError = ''; registerPasswordError = ''; registerError = ''"
            />
          </div>
          <div v-if="phoneError" class="w-full bg-[#3B1219] border border-[#5D1820] rounded-lg p-3 text-[#FB2C36] text-sm text-center">
            {{ phoneError }}
          </div>
        </div>

        <!-- Verify Code Input -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#CAD5E2]">验证码</label>
          <div class="flex gap-3">
            <div class="relative group flex-1">
              <div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-white transition-colors">
                <!-- Shield/Check Icon -->
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9 12.75L11.25 15L15 9.75M21 12C21 12 20 15 12 15C4 15 3 12 3 12V5.25C3 4.42157 3.67157 3.75 4.5 3.75H19.5C20.3284 3.75 21 4.42157 21 5.25V12Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <input 
                v-model="registerVerifyCode"
                type="text" 
                autocomplete="off"
                class="w-full bg-white/10 border border-white/20 rounded-lg pl-10 pr-3 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
                placeholder="请输入验证码"
                @input="registerError = ''"
              />
            </div>
            <button 
              type="button"
              @click="startTimer"
              :disabled="isCountingDown"
              class="px-4 py-2.5 text-sm font-medium border rounded-lg transition-all whitespace-nowrap min-w-[104px] flex items-center justify-center gap-1.5"
              :class="isCountingDown 
                ? 'text-[#62748E] bg-white/5 border-white/10 cursor-not-allowed' 
                : 'text-[#CAD5E2] bg-white/10 border-white/20 hover:text-white hover:border-white/40 hover:bg-white/15'"
            >
              <span v-if="isCountingDown" class="flex items-center gap-1.5">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" class="animate-spin-slow">
                   <path d="M7 1.75V3.5M7 10.5V12.25M1.75 7H3.5M10.5 7H12.25M3.28719 3.28719L4.52469 4.52469M9.47531 9.47531L10.7128 10.7128M3.28719 10.7128L4.52469 9.47531M9.47531 4.52469L10.7128 3.28719" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span class="text-[#62748E]">{{ countdown }}</span>
                <span class="text-[#62748E]">后重发</span>
              </span>
              <span v-else>发送验证码</span>
            </button>
          </div>
        </div>

        <!-- Password Input -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#CAD5E2]">密码</label>
          <div class="relative group">
            <div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-white transition-colors">
              <!-- Lock Icon -->
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16.5 10.5V6.75C16.5 4.26472 14.4853 2.25 12 2.25C9.51472 2.25 7.5 4.26472 7.5 6.75V10.5M3.75 10.5H20.25V21.75H3.75V10.5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 15V17.25" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <input 
              v-model="registerPassword"
              :type="showRegisterPassword ? 'text' : 'password'"
              autocomplete="new-password"
              class="w-full bg-white/10 border border-white/20 rounded-lg pl-10 pr-10 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
              placeholder="请设置密码（至少 8 位，含字母和数字）"
              @input="registerPasswordError = ''; registerError = ''"
            />
            <button 
              type="button"
              @click="toggleRegisterPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
            >
              <svg v-if="!showRegisterPassword" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
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

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-[#CAD5E2]">确认密码</label>
          <div class="relative group">
            <div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-white transition-colors">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16.5 10.5V6.75C16.5 4.26472 14.4853 2.25 12 2.25C9.51472 2.25 7.5 4.26472 7.5 6.75V10.5M3.75 10.5H20.25V21.75H3.75V10.5Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 15V17.25" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <input
              v-model="registerConfirmPassword"
              :type="showRegisterConfirmPassword ? 'text' : 'password'"
              autocomplete="new-password"
              class="w-full bg-white/10 border border-white/20 rounded-lg pl-10 pr-10 py-2.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
              placeholder="请再次输入密码"
              @input="registerConfirmPasswordError = ''"
            />
            <div v-if="registerConfirmPasswordError" class="text-red-500 text-xs mt-1">{{ registerConfirmPasswordError }}</div>
            <button
              type="button"
              @click="toggleRegisterConfirmPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
            >
              <svg v-if="!showRegisterConfirmPassword" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
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
          <div v-if="registerPasswordError" class="w-full bg-[#3B1219] border border-[#5D1820] rounded-lg p-3 text-[#FB2C36] text-sm text-center">
            {{ registerPasswordError }}
          </div>
        </div>

        <!-- Register Button -->
        <button 
          type="submit"
          :disabled="isRegistering"
          class="w-full bg-brand-blue hover:bg-blue-600 text-white text-sm font-medium py-2.5 rounded-lg transition-colors shadow-lg shadow-blue-500/20 mt-2 flex items-center justify-center gap-2"
          :class="isRegistering ? 'opacity-80 cursor-not-allowed' : ''"
        >
          <svg v-if="isRegistering" width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" class="animate-spin">
            <circle cx="8" cy="8" r="7" stroke="white" stroke-opacity="0.25" stroke-width="2"/>
            <path d="M8 1C4.13401 1 1 4.13401 1 8" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
          {{ isRegistering ? '注册中...' : '注 册' }}
        </button>

        <div v-if="registerError" class="w-full bg-[#3B1219] border border-[#5D1820] rounded-lg p-3 text-[#FB2C36] text-sm text-center">
          {{ registerError }}
        </div>

        <!-- Switch to Login -->
        <div class="flex items-center justify-center gap-1 mt-2">
          <span class="text-xs text-[#62748E]">已有账号？</span>
          <button @click="activeTab = 'login'" class="text-xs text-[#90A1B9] hover:text-white transition-colors">立即登录</button>
        </div>
      </form>
    </div>

    <!-- Footer -->
    <div class="text-center">
      <p class="text-xs text-[#45556C]">© 2024 AI Testing Platform · 企业内部测试工具</p>
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
