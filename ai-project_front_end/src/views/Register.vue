<template>
  <div class="min-h-screen flex items-center justify-center bg-brand-dark py-12 px-4 sm:px-6 lg:px-8">
    <AuthCard initial-tab="register" @register-success="handleRegisterSuccess" @login-success="handleLoginSuccess" />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import AuthCard from '@/components/AuthCard.vue'

const router = useRouter()

const handleRegisterSuccess = () => {
  // AuthCard switches to login tab automatically on register success,
  // so we might not need to do anything, or we can show a toast.
}

const handleLoginSuccess = () => {
  router.push('/projects')
}
</script>
