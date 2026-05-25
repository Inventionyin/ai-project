<template>
  <div class="min-h-screen flex items-center justify-center bg-brand-dark py-12 px-4 sm:px-6 lg:px-8">
    <AuthCard @login-success="handleLoginSuccess" />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useRoute } from 'vue-router'
import AuthCard from '@/components/AuthCard.vue'

const router = useRouter()
const route = useRoute()

const handleLoginSuccess = () => {
  const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/projects'
  router.push(redirect)
}
</script>
