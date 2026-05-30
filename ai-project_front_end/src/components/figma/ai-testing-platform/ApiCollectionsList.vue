<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiImport from '@/assets/figma/ai-testing-platform/api-import.svg'
import apiSearch from '@/assets/figma/ai-testing-platform/api-search.svg'
import apiCollection from '@/assets/figma/ai-testing-platform/api-collection.svg'
import apiCollection2 from '@/assets/figma/ai-testing-platform/api-collection-2.svg'
import apiCollection3 from '@/assets/figma/ai-testing-platform/api-collection-3.svg'
import apiFolder from '@/assets/figma/ai-testing-platform/api-folder.svg'
import apiFolder2 from '@/assets/figma/ai-testing-platform/api-folder-2.svg'
import apiAddCollection from '@/assets/figma/ai-testing-platform/api-add-collection.svg'
import CreateApiCollectionModal from '@/components/figma/ai-testing-platform/CreateApiCollectionModal.vue'
import CreateApiFolderModal from '@/components/figma/ai-testing-platform/CreateApiFolderModal.vue'
import CreateApiRequestModal from '@/components/figma/ai-testing-platform/CreateApiRequestModal.vue'
import {
  createCollection,
  createCollectionGroup,
  createCollectionRequest,
  fetchCollectionDetail,
  fetchCollections,
  fetchPostmanCloudCollections,
  syncPostmanCloudCollection,
  type CollectionDetail,
  type CollectionRequest,
  type PostmanCloudCollection
} from '@/lib/aiTestingPlatformApi'

type ApiMethod = 'POST' | 'GET' | 'PUT' | 'PATCH' | 'DELETE'

type ApiEndpoint = {
  id: string
  name: string
  method: ApiMethod
}

type FolderNode = {
  id: string
  name: string
  icon: string
  expanded: boolean
  endpoints: ApiEndpoint[]
}

type CollectionNode = {
  id: string
  name: string
  icon: string
  expanded: boolean
  folders: FolderNode[]
}

const route = useRoute()
const router = useRouter()
const collectionIcons = [apiCollection, apiCollection2, apiCollection3]
const collections = ref<CollectionNode[]>([])
const activeCollectionId = ref('')
const activeEndpointId = ref('')
const loading = ref(false)
const loadError = ref('')
const actionError = ref('')
const creatingCollection = ref(false)
const creatingFolder = ref(false)
const creatingRequest = ref(false)
const importGuideOpen = ref(false)
const postmanCloudApiKey = ref('')
const postmanCloudWorkspaceId = ref('')
const postmanCloudCollections = ref<PostmanCloudCollection[]>([])
const postmanCloudSelectedUid = ref('')
const postmanCloudLoading = ref(false)
const postmanCloudSyncing = ref(false)
const postmanCloudMessage = ref('')

const contextMenu = ref<{
  isOpen: boolean
  x: number
  y: number
  collectionId: string | null
}>({
  isOpen: false,
  x: 0,
  y: 0,
  collectionId: null
})

const isCreateCollectionOpen = ref(false)
const isCreateFolderOpen = ref(false)
const isCreateRequestOpen = ref(false)
const modalCollectionId = ref<string | null>(null)
const projectId = computed(() => String(route.params.projectId || '').trim())

function pickCollectionIcon(index: number) {
  return collectionIcons[index % collectionIcons.length]
}

function toApiMethod(method: string): ApiMethod {
  const upper = String(method || '').toUpperCase()
  if (upper === 'GET' || upper === 'POST' || upper === 'PUT' || upper === 'PATCH' || upper === 'DELETE') return upper
  return 'GET'
}

function toEndpointNode(request: CollectionRequest): ApiEndpoint {
  return {
    id: request.id,
    name: request.name,
    method: toApiMethod(request.method)
  }
}

function toCollectionNode(detail: CollectionDetail, index: number): CollectionNode {
  const folders: FolderNode[] = detail.groups.map((group, groupIndex) => ({
    id: group.id,
    name: group.name,
    icon: groupIndex % 2 === 0 ? apiFolder : apiFolder2,
    expanded: true,
    endpoints: Array.isArray(group.requests) ? group.requests.map(toEndpointNode) : []
  }))
  if (Array.isArray(detail.requests) && detail.requests.length > 0) {
    folders.push({
      id: `${detail.id}-ungrouped`,
      name: '未分组',
      icon: apiFolder2,
      expanded: true,
      endpoints: detail.requests.map(toEndpointNode)
    })
  }
  return {
    id: detail.id,
    name: detail.name,
    icon: pickCollectionIcon(index),
    expanded: index === 0,
    folders
  }
}

function initActiveSelection() {
  const firstCollection = collections.value[0]
  if (!firstCollection) {
    activeCollectionId.value = ''
    activeEndpointId.value = ''
    return
  }
  activeCollectionId.value = firstCollection.id
  const firstEndpoint = firstCollection.folders[0]?.endpoints[0]
  activeEndpointId.value = firstEndpoint?.id ?? ''
}

async function loadCollections() {
  const pid = projectId.value
  actionError.value = ''
  loadError.value = ''
  if (!pid) {
    collections.value = []
    initActiveSelection()
    return
  }
  loading.value = true
  try {
    const list = await fetchCollections(pid, 1, 200)
    const details = await Promise.all(list.map((item: { id: string }) => fetchCollectionDetail(item.id)))
    collections.value = details.map((detail: CollectionDetail, index: number) => toCollectionNode(detail, index))
    initActiveSelection()
  } catch (error) {
    collections.value = []
    initActiveSelection()
    loadError.value = error instanceof Error ? error.message : '接口集合加载失败'
  } finally {
    loading.value = false
  }
}

function closeContextMenu() {
  contextMenu.value.isOpen = false
  contextMenu.value.collectionId = null
}

function openContextMenu(e: MouseEvent, collectionId: string) {
  const maxX = Math.max(0, window.innerWidth - 180)
  const maxY = Math.max(0, window.innerHeight - 92)
  contextMenu.value = {
    isOpen: true,
    x: Math.min(e.clientX, maxX),
    y: Math.min(e.clientY, maxY),
    collectionId
  }
  activeCollectionId.value = collectionId
}

function methodStyle(method: string) {
  const upper = toApiMethod(method)
  if (upper === 'GET') return { bg: '#F0FDF4', fg: '#00A63E' }
  if (upper === 'PUT') return { bg: '#FEFCE8', fg: '#D08700' }
  if (upper === 'PATCH') return { bg: '#FFEDD4', fg: '#F54900' }
  if (upper === 'DELETE') return { bg: '#FFE2E2', fg: '#E7000B' }
  return { bg: '#EFF6FF', fg: '#155DFC' }
}

function isActiveCollection(id: string) {
  return activeCollectionId.value === id
}

function isActiveEndpoint(id: string) {
  return activeEndpointId.value === id
}

function collectionCount(c: CollectionNode) {
  return c.folders.reduce((sum, f) => sum + f.endpoints.length, 0)
}

function toggleCollection(collection: CollectionNode) {
  activeCollectionId.value = collection.id
  collection.expanded = !collection.expanded
}

function toggleFolder(collection: CollectionNode, folder: FolderNode) {
  activeCollectionId.value = collection.id
  folder.expanded = !folder.expanded
}

function selectEndpoint(collection: CollectionNode, endpoint: ApiEndpoint) {
  activeCollectionId.value = collection.id
  activeEndpointId.value = endpoint.id
  if (!projectId.value) return
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/assets/apis/${encodeURIComponent(collection.id)}?requestId=${encodeURIComponent(endpoint.id)}`)
}

function openImportGuide() {
  importGuideOpen.value = !importGuideOpen.value
}

function goActiveCollectionDebug() {
  const target = activeCollectionId.value || collections.value[0]?.id || ''
  if (!target || !projectId.value) return
  void router.push(`/projects/${encodeURIComponent(projectId.value)}/assets/apis/${encodeURIComponent(target)}`)
}

async function loadPostmanCloudCollections() {
  if (!projectId.value) return
  actionError.value = ''
  postmanCloudMessage.value = ''
  postmanCloudLoading.value = true
  try {
    const data = await fetchPostmanCloudCollections({
      projectId: projectId.value,
      apiKey: postmanCloudApiKey.value,
      workspaceId: postmanCloudWorkspaceId.value
    })
    postmanCloudCollections.value = Array.isArray(data.items) ? data.items : []
    postmanCloudSelectedUid.value = postmanCloudCollections.value[0]?.uid || ''
    postmanCloudMessage.value = postmanCloudCollections.value.length ? `已读取 ${postmanCloudCollections.value.length} 个云端集合` : '云端暂无集合'
  } catch (error) {
    postmanCloudCollections.value = []
    postmanCloudSelectedUid.value = ''
    actionError.value = error instanceof Error ? error.message : '读取 Postman 云端集合失败'
  } finally {
    postmanCloudLoading.value = false
  }
}

async function syncSelectedPostmanCloudCollection() {
  if (!projectId.value || !postmanCloudSelectedUid.value) return
  actionError.value = ''
  postmanCloudMessage.value = ''
  postmanCloudSyncing.value = true
  try {
    const data = await syncPostmanCloudCollection({
      projectId: projectId.value,
      collectionUid: postmanCloudSelectedUid.value,
      apiKey: postmanCloudApiKey.value,
      workspaceId: postmanCloudWorkspaceId.value
    })
    const node = toCollectionNode(data.collection, collections.value.length)
    const existingIndex = collections.value.findIndex((item) => item.id === node.id)
    node.expanded = true
    if (existingIndex >= 0) {
      collections.value.splice(existingIndex, 1, node)
    } else {
      collections.value.push(node)
    }
    activeCollectionId.value = node.id
    activeEndpointId.value = node.folders[0]?.endpoints[0]?.id ?? ''
    postmanCloudMessage.value = '同步完成'
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '同步 Postman 集合失败'
  } finally {
    postmanCloudSyncing.value = false
  }
}

function findCollection(collectionId: string) {
  return collections.value.find((c) => c.id === collectionId) ?? null
}

const modalCollection = computed(() => {
  if (!modalCollectionId.value) return null
  return findCollection(modalCollectionId.value)
})

const modalCollectionName = computed(() => modalCollection.value?.name ?? '')

const modalFolderOptions = computed(() => {
  const folders = modalCollection.value?.folders ?? []
  return folders.map((f) => ({ id: f.id, name: f.name }))
})

function openCreateFolderFromMenu() {
  if (!contextMenu.value.collectionId) return
  modalCollectionId.value = contextMenu.value.collectionId
  isCreateFolderOpen.value = true
  closeContextMenu()
}

function openCreateRequestFromMenu() {
  if (!contextMenu.value.collectionId) return
  modalCollectionId.value = contextMenu.value.collectionId
  isCreateRequestOpen.value = true
  closeContextMenu()
}

function closeCreateFolder() {
  isCreateFolderOpen.value = false
  modalCollectionId.value = null
}

function closeCreateRequest() {
  isCreateRequestOpen.value = false
  modalCollectionId.value = null
}

async function handleCreateFolder(payload: { name: string; description: string }) {
  if (!modalCollectionId.value) return
  const collection = findCollection(modalCollectionId.value)
  if (!collection) return
  actionError.value = ''
  creatingFolder.value = true
  try {
    const folderName = payload.name.trim()
    if (!folderName) throw new Error('文件夹名称不能为空')
    const group = await createCollectionGroup(collection.id, { name: folderName })
    collection.expanded = true
    collection.folders.push({
      id: group.id,
      name: group.name,
      icon: collection.folders.length % 2 === 0 ? apiFolder : apiFolder2,
      expanded: true,
      endpoints: []
    })
    closeCreateFolder()
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '创建文件夹失败'
  } finally {
    creatingFolder.value = false
  }
}

function normalizeRequestUrl(path: string) {
  const trimmed = String(path || '').trim()
  if (!trimmed) return '/api'
  const withLeadingSlash = trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  return withLeadingSlash.startsWith('/api') ? withLeadingSlash : `/api${withLeadingSlash}`
}

async function handleCreateRequest(payload: { method: ApiMethod; name: string; path: string; folderId: string; description: string }) {
  if (!modalCollectionId.value) return
  const collection = findCollection(modalCollectionId.value)
  if (!collection) return
  actionError.value = ''
  creatingRequest.value = true
  try {
    const apiName = payload.name.trim()
    if (!apiName) throw new Error('接口名称不能为空')
    const created = await createCollectionRequest(collection.id, {
      groupId: payload.folderId || null,
      name: apiName,
      method: payload.method,
      url: normalizeRequestUrl(payload.path),
      headers: {},
      auth: {},
      body: {},
      asserts: {}
    })
    let targetFolder = collection.folders.find((f) => f.id === (created.groupId || ''))
    if (!targetFolder) {
      const ungroupedId = `${collection.id}-ungrouped`
      targetFolder = collection.folders.find((f) => f.id === ungroupedId)
      if (!targetFolder) {
        targetFolder = {
          id: ungroupedId,
          name: '未分组',
          icon: apiFolder2,
          expanded: true,
          endpoints: []
        }
        collection.folders.push(targetFolder)
      }
    }
    collection.expanded = true
    targetFolder.expanded = true
    targetFolder.endpoints.push(toEndpointNode(created))
    activeEndpointId.value = created.id
    closeCreateRequest()
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '创建接口失败'
  } finally {
    creatingRequest.value = false
  }
}

function openCreateCollection() {
  isCreateCollectionOpen.value = true
}

function closeCreateCollection() {
  isCreateCollectionOpen.value = false
}

async function handleCreateCollection(payload: { name: string; description: string; baseUrl: string; defaultAuthType: string }) {
  if (!projectId.value) {
    actionError.value = '项目 ID 不存在'
    return
  }
  actionError.value = ''
  creatingCollection.value = true
  try {
    const name = payload.name.trim()
    if (!name) throw new Error('集合名称不能为空')
    const detail = await createCollection({
      projectId: projectId.value,
      name,
      variables: {
        description: payload.description,
        baseUrl: payload.baseUrl,
        defaultAuthType: payload.defaultAuthType
      }
    })
    const node = toCollectionNode(detail, collections.value.length)
    node.expanded = true
    collections.value.push(node)
    activeCollectionId.value = node.id
    activeEndpointId.value = node.folders[0]?.endpoints[0]?.id ?? ''
    closeCreateCollection()
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '创建集合失败'
  } finally {
    creatingCollection.value = false
  }
}

watch(projectId, () => {
  void loadCollections()
}, { immediate: true })

</script>

<template>
  <button
    v-if="contextMenu.isOpen"
    type="button"
    class="fixed inset-0 z-40"
    aria-label="Close context menu"
    @click="closeContextMenu"
  />

  <div
    v-if="contextMenu.isOpen"
    class="fixed z-50 w-[180px] overflow-hidden rounded-[10px] border border-black/10 bg-white shadow-[0px_10px_15px_-3px_rgba(0,0,0,0.1),0px_4px_6px_-4px_rgba(0,0,0,0.1)]"
    :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
  >
    <button
      type="button"
      class="block w-full px-[12px] py-[8px] text-left text-[14px] leading-[20px] text-[#0A0A0A] hover:bg-black/5"
      @click="openCreateFolderFromMenu"
    >
      新建文件夹
    </button>
    <button
      type="button"
      class="block w-full px-[12px] py-[8px] text-left text-[14px] leading-[20px] text-[#0A0A0A] hover:bg-black/5"
      @click="openCreateRequestFromMenu"
    >
      新建接口
    </button>
  </div>

  <section class="w-full md:h-full md:w-[256px] md:shrink-0 md:border-r-[0.6667px] md:border-black/10">
    <div class="flex h-full w-full flex-col bg-[rgba(236,236,240,0.2)]">
      <div class="flex flex-col gap-[8px] border-b-[0.6667px] border-black/10 px-[12px] pt-[12px] pb-[0.67px]">
        <div class="flex items-center justify-between">
          <div class="h-[16px] w-[48px] text-[12px] font-semibold leading-[16px] text-[#717182]">接口集合</div>
          <button type="button" class="relative h-[16px] w-[39px]" aria-label="导入接口集合" @click="openImportGuide">
            <img :src="apiImport" alt="" class="absolute left-0 top-[2.5px] h-[11px] w-[11px]" />
            <span class="absolute left-[13px] top-0 h-[16px] w-[28px] text-center text-[12px] font-medium leading-[16px] text-[#155DFC]">
              导入
            </span>
          </button>
        </div>

        <div v-if="importGuideOpen" class="rounded-[8px] border border-[#BEDBFF] bg-white p-[8px]">
          <div class="text-[12px] font-semibold leading-[16px] text-[#0A0A0A]">Postman / Swagger / OpenAPI</div>
          <div class="mt-[4px] text-[11px] leading-[16px] text-[#717182]">
            导入后进入集合详情页进行单请求运行、保存、导出和绑定用例
          </div>
          <div class="mt-[8px] grid gap-[6px]">
            <input
              v-model="postmanCloudApiKey"
              type="password"
              autocomplete="off"
              class="h-[28px] w-full rounded-[8px] border border-black/10 px-[8px] text-[12px] leading-[16px] outline-none focus:border-[#155DFC]"
              placeholder="Postman API Key"
            />
            <input
              v-model="postmanCloudWorkspaceId"
              class="h-[28px] w-full rounded-[8px] border border-black/10 px-[8px] text-[12px] leading-[16px] outline-none focus:border-[#155DFC]"
              placeholder="Workspace ID"
            />
            <button
              type="button"
              class="h-[28px] w-full rounded-[8px] border border-[#155DFC]/30 bg-white text-[12px] font-medium text-[#155DFC] disabled:opacity-50"
              :disabled="postmanCloudLoading || !projectId"
              @click="loadPostmanCloudCollections"
            >
              {{ postmanCloudLoading ? '读取中...' : '读取云端集合' }}
            </button>
            <select
              v-if="postmanCloudCollections.length"
              v-model="postmanCloudSelectedUid"
              class="h-[28px] w-full rounded-[8px] border border-black/10 bg-white px-[8px] text-[12px] leading-[16px] outline-none focus:border-[#155DFC]"
            >
              <option v-for="item in postmanCloudCollections" :key="item.uid" :value="item.uid">
                {{ item.name }}
              </option>
            </select>
            <button
              v-if="postmanCloudCollections.length"
              type="button"
              class="h-[28px] w-full rounded-[8px] bg-[#155DFC] text-[12px] font-medium text-white disabled:opacity-50"
              :disabled="postmanCloudSyncing || !postmanCloudSelectedUid"
              @click="syncSelectedPostmanCloudCollection"
            >
              {{ postmanCloudSyncing ? '同步中...' : '同步到平台' }}
            </button>
            <div v-if="postmanCloudMessage" class="text-[11px] leading-[16px] text-[#717182]">{{ postmanCloudMessage }}</div>
          </div>
          <button
            type="button"
            class="mt-[8px] h-[28px] w-full rounded-[8px] bg-[#155DFC] text-[12px] font-medium text-white disabled:opacity-50"
            :disabled="!activeCollectionId && collections.length === 0"
            @click="goActiveCollectionDebug"
          >
            去当前集合调试
          </button>
        </div>

        <div class="relative h-[28px] w-full rounded-[10px] border border-black/10 bg-white pl-[28px] pr-[8px]">
          <img :src="apiSearch" alt="" class="absolute left-[10px] top-[8px] h-[12px] w-[12px]" />
          <div class="flex h-full items-center text-[12px] leading-[16px] text-[#0A0A0A]">搜索接口...</div>
        </div>
      </div>

      <div class="flex min-h-0 flex-1 flex-col gap-[2px] overflow-auto px-[8px] pt-[12px]">
        <div v-if="loading" class="px-[8px] py-[6px] text-[12px] leading-[16px] text-[#717182]">正在加载接口集合...</div>
        <div v-else-if="loadError" class="px-[8px] py-[6px] text-[12px] leading-[16px] text-[#E7000B]">{{ loadError }}</div>
        <div v-else-if="collections.length === 0" class="px-[8px] py-[6px] text-[12px] leading-[16px] text-[#717182]">暂无接口集合</div>
        <div v-for="collection in collections" :key="collection.id" class="flex flex-col gap-[2px]">
          <button
            type="button"
            class="flex h-[28px] w-full items-center gap-[8px] rounded-[10px] px-[8px]"
            :class="isActiveCollection(collection.id) ? 'bg-[#DBEAFE]' : ''"
            @click="toggleCollection(collection)"
            @contextmenu.prevent.stop="openContextMenu($event, collection.id)"
          >
            <img :src="collection.icon" alt="" class="h-[12px] w-[12px]" />
            <div
              class="flex-1 text-left text-[12px] font-medium leading-[16px]"
              :class="isActiveCollection(collection.id) ? 'text-[#1447E6]' : 'text-[#717182]'"
            >
              {{ collection.name }}
            </div>
            <div
              class="w-[14.08px] text-center text-[12px] font-medium leading-[16px] opacity-60"
              :class="isActiveCollection(collection.id) ? 'text-[#1447E6]' : 'text-[#717182]'"
            >
              {{ collectionCount(collection) }}
            </div>
          </button>

          <div v-if="collection.expanded && collection.folders.length > 0" class="flex flex-col">
            <div
              v-for="folder in collection.folders"
              :key="folder.id"
              class="flex flex-col gap-[2px] pl-[16px] pt-[6px]"
            >
              <button
                type="button"
                class="flex h-[28px] items-center gap-[8px] rounded-[10px] px-[8px]"
                @click="toggleFolder(collection, folder)"
              >
                <img :src="folder.icon" alt="" class="h-[12px] w-[12px]" />
                <span class="text-[12px] font-medium leading-[16px] text-[#717182]">
                  {{ folder.name }}
                </span>
              </button>

              <div v-if="folder.expanded" class="flex flex-col gap-[2px]">
                <button
                  v-for="endpoint in folder.endpoints"
                  :key="endpoint.id"
                  type="button"
                  class="flex h-[28px] items-center gap-[8px] rounded-[10px] pl-[24px]"
                  :class="isActiveEndpoint(endpoint.id) ? 'bg-[#EFF6FF]' : ''"
                  @click="selectEndpoint(collection, endpoint)"
                >
                  <span
                    class="flex h-[16px] w-[40px] items-center justify-center rounded-[4px] text-[12px] font-medium leading-[16px]"
                    :style="{ background: methodStyle(endpoint.method).bg, color: methodStyle(endpoint.method).fg, fontFamily: 'Consolas' }"
                  >
                    {{ endpoint.method }}
                  </span>
                  <span
                    class="text-[12px] font-medium leading-[16px]"
                    :class="isActiveEndpoint(endpoint.id) ? 'text-[#1447E6]' : 'text-[#0A0A0A]'"
                  >
                    {{ endpoint.name }}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="px-[8px] pb-[12px]">
        <div v-if="actionError" class="px-[8px] py-[4px] text-[12px] leading-[16px] text-[#E7000B]">{{ actionError }}</div>
        <button
          type="button"
          class="mt-[6px] flex h-[28px] w-full items-center gap-[8px] rounded-[10px] px-[8px]"
          :disabled="creatingCollection || creatingFolder || creatingRequest"
          @click="openCreateCollection"
        >
          <img :src="apiAddCollection" alt="" class="h-[12px] w-[12px]" />
          <span class="text-center text-[12px] font-medium leading-[16px] text-[#155DFC]">新建集合</span>
        </button>
      </div>
    </div>
  </section>

  <CreateApiCollectionModal :is-open="isCreateCollectionOpen" @close="closeCreateCollection" @create="handleCreateCollection" />
  <CreateApiFolderModal :is-open="isCreateFolderOpen" :collection-name="modalCollectionName" @close="closeCreateFolder" @create="handleCreateFolder" />
  <CreateApiRequestModal
    :is-open="isCreateRequestOpen"
    :collection-name="modalCollectionName"
    :folders="modalFolderOptions"
    @close="closeCreateRequest"
    @create="handleCreateRequest"
  />
</template>
