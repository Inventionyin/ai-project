<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

type RoleKey = 'admin' | 'editor' | 'viewer'

const selectedRole = ref<RoleKey>('admin')
const route = useRoute()
const projectSettingsHref = computed(() => {
  const rawProjectId = typeof route.params.projectId === 'string' ? route.params.projectId.trim() : ''
  const projectId = rawProjectId || '1'
  return `/projects/${encodeURIComponent(projectId)}/settings`
})

const roles: Array<{
  key: RoleKey
  label: string
  description: string
  scope: string
}> = [
  {
    key: 'admin',
    label: '管理员',
    description: '可管理成员、项目配置、外部集成和验收放行。',
    scope: '成员管理 / 平台配置 / 安全审计'
  },
  {
    key: 'editor',
    label: '编辑者',
    description: '可维护需求、用例、接口和执行资产。',
    scope: '资产维护 / 自动化执行 / 报告查看'
  },
  {
    key: 'viewer',
    label: '查看者',
    description: '只读查看资产、报告、仪表盘和验收结论。',
    scope: '只读查看 / 导出报告'
  }
]

const selectedRoleInfo = computed(() => roles.find((role) => role.key === selectedRole.value) || roles[0])

const members = [
  { name: '项目管理员', email: 'admin@example.com', role: '管理员' },
  { name: '测试负责人', email: 'qa-lead@example.com', role: '编辑者' },
  { name: '业务验收人', email: 'reviewer@example.com', role: '查看者' }
]
</script>

<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-4 md:p-6">
    <div class="flex flex-col gap-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 class="text-[16px] font-semibold leading-6 text-[#0A0A0A]">权限与成员</h1>
          <p class="mt-1 text-[12px] leading-4 text-[#717182]">内部平台仅保留邮箱密码登录，权限按项目角色收敛。</p>
        </div>
        <RouterLink
          :to="projectSettingsHref"
          class="inline-flex h-9 items-center justify-center rounded-[8px] bg-[#155DFC] px-4 text-[13px] font-medium text-white"
        >
          进入项目设置
        </RouterLink>
      </div>

      <section class="rounded-[10px] border border-black/10 bg-white p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div class="text-[14px] font-semibold leading-5 text-[#0A0A0A]">角色模板</div>
            <div class="mt-1 text-[12px] leading-4 text-[#717182]">先选择角色，再查看该角色允许的操作范围。</div>
          </div>
          <label class="flex items-center gap-2 text-[12px] leading-4 text-[#717182]">
            选择项目角色
            <select
              v-model="selectedRole"
              aria-label="选择项目角色"
              class="h-9 min-w-[160px] rounded-[8px] border border-black/10 bg-white px-3 text-[13px] text-[#0A0A0A] outline-none focus:border-[#155DFC]"
            >
              <option v-for="role in roles" :key="role.key" :value="role.key">
                {{ role.label }}
              </option>
            </select>
          </label>
        </div>

        <div class="mt-4 rounded-[8px] border border-[#155DFC]/30 bg-[#F8FBFF] p-4">
          <div class="text-[13px] font-semibold leading-5 text-[#0A0A0A]">{{ selectedRoleInfo.label }}</div>
          <div class="mt-1 text-[12px] leading-5 text-[#374151]">{{ selectedRoleInfo.description }}</div>
          <div class="mt-3 inline-flex rounded-full bg-white px-3 py-1 text-[12px] font-medium text-[#155DFC]">
            {{ selectedRoleInfo.scope }}
          </div>
        </div>
      </section>

      <section class="rounded-[10px] border border-black/10 bg-white p-4">
        <div class="mb-3 text-[14px] font-semibold leading-5 text-[#0A0A0A]">成员列表</div>
        <div class="grid grid-cols-1 gap-2 md:grid-cols-3">
          <div v-for="member in members" :key="member.email" class="rounded-[8px] border border-black/10 p-3">
            <div class="text-[13px] font-semibold leading-5 text-[#0A0A0A]">{{ member.name }}</div>
            <div class="mt-1 text-[12px] leading-4 text-[#717182]">{{ member.email }}</div>
            <div class="mt-3 inline-flex rounded-full bg-[#F8FAFC] px-3 py-1 text-[12px] text-[#374151]">{{ member.role }}</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
