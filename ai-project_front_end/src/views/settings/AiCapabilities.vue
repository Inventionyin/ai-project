<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="mb-4">
        <div class="text-[16px] font-semibold text-[#0A0A0A]">AI 能力中心</div>
        <div class="text-[12px] text-[#717182] mt-1">平台 AI 能力入口，快速访问需求分析、用例生成和变更影响分析</div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div v-for="cap in capabilities" :key="cap.title" class="border border-black/10 rounded p-4 hover:border-[#155DFC] transition-colors">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded bg-blue-50 flex items-center justify-center text-[14px]">{{ cap.icon }}</div>
            <div class="text-[14px] font-medium">{{ cap.title }}</div>
          </div>
          <div class="text-[12px] text-[#717182] mb-3">{{ cap.description }}</div>
          <div class="flex items-center gap-2 mb-3">
            <span :class="cap.status === '可用' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'" class="px-2 py-0.5 rounded text-[11px]">{{ cap.status }}</span>
          </div>
          <router-link :to="cap.to" class="block text-center text-[12px] px-3 py-1 bg-[#155DFC] text-white rounded hover:bg-blue-700">
            {{ cap.action }}
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const projectId = computed(() => route.params.projectId as string)

const capabilities = computed(() => [
  {
    icon: '📊',
    title: '需求智能分析',
    description: '对需求文档进行结构化分析，生成功能点、业务规则、风险点和测试建议',
    status: '可用',
    action: '进入需求文档',
    to: `/projects/${projectId.value}/requirements/docs`
  },
  {
    icon: '🧪',
    title: 'AI 用例生成',
    description: '基于分析结果自动生成测试用例草稿，支持批量审核入库',
    status: '可用',
    action: '进入用例管理',
    to: `/projects/${projectId.value}/assets/testcases`
  },
  {
    icon: '🔄',
    title: '变更影响分析',
    description: '对比需求版本差异，识别变更项并自动生成回归测试集',
    status: '可用',
    action: '进入需求文档',
    to: `/projects/${projectId.value}/requirements/docs`
  }
])
</script>
