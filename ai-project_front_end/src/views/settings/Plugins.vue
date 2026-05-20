<template>
  <div class="min-h-[calc(100vh-48px)] w-full bg-[rgba(236,236,240,0.3)] p-6">
    <div class="rounded-[14px] border border-black/10 bg-white p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <div class="text-[16px] font-semibold text-[#0A0A0A]">插件市场</div>
          <div class="text-[12px] text-[#717182] mt-1">浏览、安装和管理平台插件</div>
        </div>
        <div class="flex gap-2">
          <button @click="tab = 'market'" :class="tab === 'market' ? 'bg-[#155DFC] text-white' : 'border'" class="text-[12px] px-3 py-1 rounded">插件市场</button>
          <button @click="tab = 'installed'" :class="tab === 'installed' ? 'bg-[#155DFC] text-white' : 'border'" class="text-[12px] px-3 py-1 rounded">已安装</button>
        </div>
      </div>

      <!-- Market tab -->
      <div v-if="tab === 'market'">
        <div v-if="loading" class="text-center py-8 text-[12px] text-[#717182]">加载中...</div>
        <div v-else-if="plugins.length === 0" class="text-center py-8 text-[12px] text-[#717182]">暂无可用插件</div>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="p in plugins" :key="p.id" class="border border-black/10 rounded p-4">
            <div class="flex items-center justify-between mb-2">
              <div class="text-[14px] font-medium">{{ p.name }}</div>
              <span class="text-[11px] text-[#717182]">v{{ p.version }}</span>
            </div>
            <div class="text-[11px] text-[#717182] space-y-1">
              <div>{{ p.description || '暂无描述' }}</div>
              <div>类型: {{ p.pluginType }} · 作者: {{ p.author || '-' }}</div>
              <div>下载: {{ p.downloadCount }}</div>
              <div v-if="p.minPlatformVersion">最低平台版本: {{ p.minPlatformVersion }}</div>
            </div>
            <button @click="install(p.id)" class="mt-3 text-[11px] px-3 py-1 bg-[#155DFC] text-white rounded hover:bg-blue-700 w-full">安装到项目</button>
          </div>
        </div>
      </div>

      <!-- Installed tab -->
      <div v-if="tab === 'installed'">
        <div v-if="loading" class="text-center py-8 text-[12px] text-[#717182]">加载中...</div>
        <div v-else-if="installations.length === 0" class="text-center py-8 text-[12px] text-[#717182]">暂未安装插件</div>
        <div v-else class="space-y-3">
          <div v-for="inst in installations" :key="inst.id" class="border border-black/10 rounded p-4">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-[14px] font-medium">{{ inst.pluginName || inst.pluginSlug || inst.pluginId }}</div>
                <div class="text-[11px] text-[#717182] mt-1">版本: {{ inst.installedVersion }} · 状态: {{ inst.status }}</div>
              </div>
              <div class="flex items-center gap-2">
                <button @click="invoke(inst)" class="text-[11px] px-2 py-0.5 bg-green-500 text-white rounded hover:bg-green-600">调用</button>
                <button @click="toggleInstall(inst)" class="text-[11px] px-2 py-0.5 border rounded hover:bg-gray-50">
                  {{ inst.status === 'INSTALLED' ? '停用' : '启用' }}
                </button>
                <button @click="uninstall(inst.id)" class="text-[11px] px-2 py-0.5 bg-red-500 text-white rounded hover:bg-red-600">卸载</button>
              </div>
            </div>
            <div v-if="inst.errorMessage" class="text-[11px] text-red-500 mt-1">{{ inst.errorMessage }}</div>
          </div>
        </div>

        <!-- Invoke result -->
        <div v-if="invokeResult" class="mt-4 p-3 border border-green-200 bg-green-50 rounded text-[12px]">
          <div class="font-medium text-green-700">调用成功</div>
          <div class="text-[#717182] mt-1">插件: {{ invokeResult.pluginSlug }} · 状态: {{ invokeResult.status }}</div>
        </div>
        <div v-if="invokeError" class="mt-4 p-3 border border-red-200 bg-red-50 rounded text-[12px]">
          <div class="font-medium text-red-700">调用失败</div>
          <div class="text-red-500 mt-1">{{ invokeError }}</div>
        </div>

        <!-- Invocations history -->
        <div v-if="selectedInstId" class="mt-4">
          <div class="text-[13px] font-medium mb-2">调用记录</div>
          <div v-if="invocations.length === 0" class="text-[12px] text-[#717182]">暂无调用记录</div>
          <table v-else class="w-full text-[12px]">
            <thead>
              <tr class="border-b border-black/5">
                <th class="text-left py-2 px-2 text-[#717182] font-medium">记录ID</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">插件</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">状态</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">调用者</th>
                <th class="text-left py-2 px-2 text-[#717182] font-medium">时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in invocations" :key="r.id" class="border-b border-black/5">
                <td class="py-2 px-2 font-mono text-[11px]">{{ r.id.slice(0, 8) }}...</td>
                <td class="py-2 px-2">{{ r.pluginSlug || '-' }}</td>
                <td class="py-2 px-2">
                  <span :class="r.status === 'SUCCESS' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'" class="px-2 py-0.5 rounded text-[11px]">{{ r.status }}</span>
                </td>
                <td class="py-2 px-2">{{ r.invokedBy || '-' }}</td>
                <td class="py-2 px-2">{{ new Date(r.createdAt * 1000).toLocaleString('zh-CN') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { listPlugins, installPlugin, listInstallations, uninstallPlugin, togglePlugin, invokePlugin, listPluginInvocations, type Plugin, type PluginInstallation, type PluginInvokeResponse, type PluginInvokeRecord } from '@/lib/api/plugins'

const route = useRoute()
const projectId = route.params.projectId as string

const tab = ref<'market' | 'installed'>('market')
const plugins = ref<Plugin[]>([])
const installations = ref<PluginInstallation[]>([])
const loading = ref(false)
const invokeResult = ref<PluginInvokeResponse | null>(null)
const invokeError = ref<string | null>(null)
const invocations = ref<PluginInvokeRecord[]>([])
const selectedInstId = ref<string | null>(null)

async function loadMarket() {
  loading.value = true
  try {
    const res = await listPlugins()
    plugins.value = res.items
  } finally {
    loading.value = false
  }
}

async function loadInstalled() {
  loading.value = true
  try {
    const res = await listInstallations(projectId)
    installations.value = res.items
  } finally {
    loading.value = false
  }
}

async function install(pluginId: string) {
  await installPlugin(projectId, pluginId)
  await loadMarket()
}

async function uninstall(installationId: string) {
  await uninstallPlugin(projectId, installationId)
  await loadInstalled()
}

async function toggleInstall(inst: PluginInstallation) {
  await togglePlugin(projectId, inst.id, inst.status !== 'INSTALLED')
  await loadInstalled()
}

async function invoke(inst: PluginInstallation) {
  invokeResult.value = null
  invokeError.value = null
  try {
    invokeResult.value = await invokePlugin(projectId, inst.id)
    await loadInvocations(inst.id)
  } catch (e: unknown) {
    invokeError.value = e instanceof Error ? e.message : '调用失败'
  }
}

async function loadInvocations(installationId: string) {
  selectedInstId.value = installationId
  const res = await listPluginInvocations(projectId, installationId)
  invocations.value = res.items
}

watch(tab, (v) => {
  if (v === 'market') loadMarket()
  else loadInstalled()
})

onMounted(loadMarket)
</script>
