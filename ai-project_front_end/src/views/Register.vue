<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  router.replace('/login')
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-brand-dark py-12 px-4 text-sm text-[#90A1B9]">
    正在跳转到登录页...
  </div>
</template>
