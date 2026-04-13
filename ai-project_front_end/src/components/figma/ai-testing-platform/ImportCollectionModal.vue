<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import {
  createApiCollectionImportJob,
  uploadApiCollectionImportFile,
  fetchApiCollectionImportJob,
  commitApiCollectionImportJob,
  type ApiImportPreviewResult,
  type ApiImportPreviewRequest
} from '@/lib/aiTestingPlatformApi'

const props = defineProps<{
  isOpen: boolean
  projectId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'success'): void
}>()

const step = ref<1 | 2 | 3>(1)
const currentJobId = ref<string | null>(null)
const errorMsg = ref<string>('')
const loadingMsg = ref<string>('')

// Step 1: Upload
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)

// Step 2: Polling
let pollTimer: number | null = null
let pollBusy = false

// Step 3: Preview
const previewData = ref<ApiImportPreviewResult | null>(null)
const warnings = ref<any[]>([])
const selectedRequests = ref<Set<string>>(new Set()) // method + '|' + url
const overrideExisting = ref(true)

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    resetState()
  } else {
    stopPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})

function resetState() {
  step.value = 1
  currentJobId.value = null
  errorMsg.value = ''
  loadingMsg.value = ''
  selectedFile.value = null
  previewData.value = null
  warnings.value = []
  selectedRequests.value.clear()
  overrideExisting.value = true
}

function handleClose() {
  emit('close')
}

// Upload Handlers
function onDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    validateAndSetFile(files[0])
  }
}

function onFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    validateAndSetFile(target.files[0])
  }
}

function validateAndSetFile(file: File) {
  errorMsg.value = ''
  if (file.size > 10 * 1024 * 1024) {
    errorMsg.value = '文件大小不能超过 10MB'
    return
  }
  selectedFile.value = file
}

async function startUpload() {
  if (!selectedFile.value || !props.projectId) return
  
  errorMsg.value = ''
  loadingMsg.value = '正在创建导入任务...'
  
  try {
    const jobRes = await createApiCollectionImportJob(props.projectId)
    if (!jobRes?.jobId) throw new Error('未能获取 jobId')
    
    currentJobId.value = jobRes.jobId
    loadingMsg.value = '正在上传文件...'
    
    await uploadApiCollectionImportFile(currentJobId.value!, selectedFile.value)
    
    step.value = 2
    loadingMsg.value = '文件解析中，请稍候...'
    startPolling(currentJobId.value)
  } catch (err: any) {
    errorMsg.value = err.message || '上传失败'
    loadingMsg.value = ''
  }
}

// Polling Handlers
function startPolling(jobId: string) {
  stopPolling()
  const startedAt = Date.now()
  let continuousErrors = 0
  pollTimer = window.setInterval(async () => {
    if (pollBusy) return
    pollBusy = true
    try {
      const detail = await fetchApiCollectionImportJob(jobId)
      if (!detail) {
        continuousErrors += 1
        if (continuousErrors >= 3) {
          stopPolling()
          loadingMsg.value = ''
          errorMsg.value = '轮询任务状态失败，请重试'
          step.value = 1
        }
        return
      }
      continuousErrors = 0
      
      if (detail.status === 'PARSED_PREVIEW') {
        stopPolling()
        previewData.value = detail.previewData || { collectionName: selectedFile.value?.name || 'Imported Collection', groups: [] }
        warnings.value = detail.warnings || []
        initSelection()
        step.value = 3
      } else if (detail.status === 'FAILED') {
        stopPolling()
        errorMsg.value = '解析失败'
        loadingMsg.value = ''
        step.value = 1
      } else if (Date.now() - startedAt > 180000) {
        stopPolling()
        loadingMsg.value = ''
        errorMsg.value = '解析超时，请重试上传'
        step.value = 1
      }
    } catch {
      continuousErrors += 1
      if (continuousErrors >= 3) {
        stopPolling()
        loadingMsg.value = ''
        errorMsg.value = '无法获取导入状态，请检查网络或重新登录后重试'
        step.value = 1
      }
    } finally {
      pollBusy = false
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  pollBusy = false
}

// Preview Handlers
function initSelection() {
  selectedRequests.value.clear()
  if (!previewData.value) return
  
  previewData.value.groups.forEach(g => {
    g.requests.forEach(r => {
      // Default check new and updated
      if (r.diffStatus !== 'unchanged') {
        selectedRequests.value.add(getReqKey(r))
      }
    })
  })
}

function getReqKey(req: ApiImportPreviewRequest) {
  return `${req.method}|${req.url}`
}

function toggleRequestSelection(req: ApiImportPreviewRequest) {
  const key = getReqKey(req)
  if (selectedRequests.value.has(key)) {
    selectedRequests.value.delete(key)
  } else {
    selectedRequests.value.add(key)
  }
}

function toggleAllSelection() {
  const allKeys = new Set<string>()
  previewData.value?.groups.forEach(g => {
    g.requests.forEach(r => {
      allKeys.add(getReqKey(r))
    })
  })
  
  if (selectedRequests.value.size === allKeys.size) {
    selectedRequests.value.clear()
  } else {
    selectedRequests.value = allKeys
  }
}

const allSelected = computed(() => {
  let total = 0
  previewData.value?.groups.forEach(g => {
    total += g.requests.length
  })
  return total > 0 && selectedRequests.value.size === total
})

const diffBadgeColor = (status: string) => {
  if (status === 'new') return 'bg-green-100 text-green-700'
  if (status === 'updated') return 'bg-yellow-100 text-yellow-700'
  return 'bg-gray-100 text-gray-700'
}

const diffBadgeText = (status: string) => {
  if (status === 'new') return '新增'
  if (status === 'updated') return '修改'
  return '无变化'
}

async function handleCommit() {
  if (!currentJobId.value || !previewData.value) return
  
  const selectedReqsToCommit: ApiImportPreviewRequest[] = []
  previewData.value.groups.forEach(g => {
    g.requests.forEach(r => {
      if (selectedRequests.value.has(getReqKey(r))) {
        selectedReqsToCommit.push(r)
      }
    })
  })
  
  if (selectedReqsToCommit.length === 0) {
    errorMsg.value = '请至少选择一个接口导入'
    return
  }
  
  loadingMsg.value = '正在导入入库...'
  errorMsg.value = ''
  
  try {
    await commitApiCollectionImportJob(currentJobId.value, {
      selectedRequests: selectedReqsToCommit,
      overrideExisting: overrideExisting.value
    })
    emit('success')
  } catch (err: any) {
    errorMsg.value = err.message || '导入失败'
  } finally {
    loadingMsg.value = ''
  }
}

</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/40">
    <div class="relative flex w-[640px] max-w-[90vw] flex-col rounded-[16px] bg-[#FFFFFF] shadow-2xl overflow-hidden max-h-[80vh]">
      <!-- Header -->
      <div class="flex items-center justify-between border-b-[0.6667px] border-black/10 px-[24px] py-[16px]">
        <div class="text-[16px] font-semibold text-[#0A0A0A]">导入接口集合</div>
        <button type="button" class="text-[#717182] hover:text-black" @click="handleClose">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 4L4 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M4 4L12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
      
      <!-- Error Banner -->
      <div v-if="errorMsg" class="bg-red-50 text-red-600 px-[24px] py-[8px] text-[13px] border-b border-red-100">
        {{ errorMsg }}
      </div>
      
      <div v-if="warnings.length > 0 && step === 3" class="bg-yellow-50 text-yellow-700 px-[24px] py-[8px] text-[13px] border-b border-yellow-100 max-h-[100px] overflow-auto">
        <div class="font-medium mb-1">解析警告：</div>
        <ul class="list-disc pl-4">
          <li v-for="(warn, i) in warnings" :key="i">{{ warn.message || warn }}</li>
        </ul>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-auto p-[24px] bg-[#F8F9FA]">
        
        <!-- Step 1: Upload -->
        <div v-if="step === 1" class="flex flex-col gap-[16px]">
          <div 
            class="flex flex-col items-center justify-center border-2 border-dashed rounded-[12px] p-[40px] transition-colors"
            :class="isDragging ? 'border-[#155DFC] bg-[#EBF1FF]' : 'border-[#D9D9D9] bg-white hover:border-[#155DFC]'"
            @dragover="onDragOver"
            @dragleave="onDragLeave"
            @drop="onDrop"
            @click="fileInput?.click()"
          >
            <input type="file" ref="fileInput" class="hidden" accept=".md,.markdown,.json,.txt" @change="onFileSelect" />
            <svg class="w-[40px] h-[40px] text-[#717182] mb-[16px]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
            <div class="text-[15px] font-medium text-[#0A0A0A] mb-[4px]">点击或拖拽文件到此处上传</div>
            <div class="text-[13px] text-[#717182]">支持 Markdown 或 Postman JSON (大小不超过10MB)</div>
          </div>
          
          <div v-if="selectedFile" class="flex items-center justify-between bg-white p-[12px] rounded-[8px] border border-[#E5E5E5]">
            <div class="flex items-center gap-[8px]">
              <svg class="w-[20px] h-[20px] text-[#155DFC]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              <span class="text-[14px] text-[#0A0A0A]">{{ selectedFile.name }}</span>
            </div>
            <span class="text-[13px] text-[#717182]">{{ (selectedFile.size / 1024).toFixed(1) }} KB</span>
          </div>
        </div>

        <!-- Step 2: Parsing -->
        <div v-else-if="step === 2" class="flex flex-col items-center justify-center py-[60px]">
          <div class="w-[40px] h-[40px] border-4 border-[#E5E5E5] border-t-[#155DFC] rounded-full animate-spin mb-[16px]"></div>
          <div class="text-[15px] font-medium text-[#0A0A0A]">{{ loadingMsg || '解析中...' }}</div>
          <div class="text-[13px] text-[#717182] mt-[8px]">这可能需要一点时间，请耐心等待</div>
        </div>

        <!-- Step 3: Preview -->
        <div v-else-if="step === 3 && previewData" class="flex flex-col h-full bg-white border border-[#E5E5E5] rounded-[8px] overflow-hidden">
          <div class="flex items-center justify-between bg-[#F4F4F5] px-[16px] py-[12px] border-b border-[#E5E5E5]">
            <div class="font-medium text-[14px] text-[#0A0A0A]">集合名称: {{ previewData.collectionName }}</div>
            <label class="flex items-center gap-[6px] text-[13px] text-[#0A0A0A] cursor-pointer">
              <input type="checkbox" v-model="overrideExisting" class="rounded border-gray-300 text-[#155DFC] focus:ring-[#155DFC]" />
              覆盖已存在接口
            </label>
          </div>
          
          <div class="flex items-center px-[16px] py-[8px] bg-white border-b border-[#E5E5E5]">
            <label class="flex items-center gap-[8px] text-[13px] text-[#0A0A0A] cursor-pointer">
              <input type="checkbox" :checked="allSelected" @change="toggleAllSelection" class="rounded border-gray-300 text-[#155DFC] focus:ring-[#155DFC]" />
              全选
            </label>
          </div>

          <div class="flex-1 overflow-auto p-[12px] flex flex-col gap-[16px]">
            <div v-for="(group, gIdx) in previewData.groups" :key="gIdx" class="flex flex-col gap-[8px]">
              <div class="text-[13px] font-semibold text-[#717182] flex items-center gap-[6px]">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path></svg>
                {{ group.name }}
              </div>
              <div class="flex flex-col gap-[4px] pl-[16px]">
                <div v-for="(req, rIdx) in group.requests" :key="rIdx" class="flex items-center justify-between p-[8px] hover:bg-[#F4F4F5] rounded-[6px] group">
                  <label class="flex items-center gap-[12px] cursor-pointer flex-1 min-w-0">
                    <input 
                      type="checkbox" 
                      :checked="selectedRequests.has(getReqKey(req))"
                      @change="toggleRequestSelection(req)"
                      class="rounded border-gray-300 text-[#155DFC] focus:ring-[#155DFC]" 
                    />
                    <div class="flex items-center gap-[8px] flex-1 min-w-0">
                      <span class="text-[12px] font-medium w-[48px] text-[#155DFC]">{{ req.method }}</span>
                      <span class="text-[13px] text-[#0A0A0A] font-medium truncate">{{ req.name }}</span>
                      <span class="text-[12px] text-[#717182] truncate flex-1">{{ req.url }}</span>
                    </div>
                  </label>
                  <span class="text-[11px] px-[6px] py-[2px] rounded-[4px] ml-[12px]" :class="diffBadgeColor(req.diffStatus)">
                    {{ diffBadgeText(req.diffStatus) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end gap-[12px] border-t-[0.6667px] border-black/10 px-[24px] py-[16px] bg-white">
        <button 
          type="button" 
          class="h-[32px] rounded-[6px] px-[16px] text-[14px] font-medium text-[#0A0A0A] hover:bg-[#F4F4F5] transition-colors"
          @click="handleClose"
          :disabled="!!loadingMsg"
        >
          取消
        </button>
        
        <button 
          v-if="step === 1"
          type="button" 
          class="flex h-[32px] items-center justify-center rounded-[6px] bg-[#155DFC] px-[16px] text-[14px] font-medium text-white hover:bg-[#0D45C9] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="!selectedFile || !!loadingMsg"
          @click="startUpload"
        >
          <span v-if="loadingMsg" class="w-[14px] h-[14px] border-2 border-white/30 border-t-white rounded-full animate-spin mr-[8px]"></span>
          {{ loadingMsg ? '处理中...' : '开始上传解析' }}
        </button>

        <button 
          v-if="step === 3"
          type="button" 
          class="flex h-[32px] items-center justify-center rounded-[6px] bg-[#155DFC] px-[16px] text-[14px] font-medium text-white hover:bg-[#0D45C9] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="selectedRequests.size === 0 || !!loadingMsg"
          @click="handleCommit"
        >
          <span v-if="loadingMsg" class="w-[14px] h-[14px] border-2 border-white/30 border-t-white rounded-full animate-spin mr-[8px]"></span>
          {{ loadingMsg ? '导入中...' : `确认导入 (${selectedRequests.size})` }}
        </button>
      </div>
    </div>
  </div>
</template>
