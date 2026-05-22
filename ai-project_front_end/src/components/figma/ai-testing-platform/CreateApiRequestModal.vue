<script setup lang="ts">
import { computed, reactive } from 'vue'
import modalClose28 from '@/assets/figma/ai-testing-platform/modal-close-28.svg'
import modalDescIcon from '@/assets/figma/ai-testing-platform/modal-desc-icon.svg'
import modalCreateIcon from '@/assets/figma/ai-testing-platform/modal-create-icon.svg'
import filterChevron from '@/assets/figma/ai-testing-platform/filter-chevron.svg'

type ApiMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

const props = defineProps<{
  isOpen: boolean
  collectionName: string
  folders: Array<{ id: string; name: string }>
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'create', payload: { method: ApiMethod; name: string; path: string; folderId: string; description: string }): void
}>()

const formData = reactive({
  method: 'GET' as ApiMethod,
  name: '',
  path: '/v1/users',
  folderId: '',
  description: ''
})

const folderIdResolved = computed(() => {
  if (formData.folderId) return formData.folderId
  return props.folders[0]?.id ?? ''
})

function handleClose() {
  emit('close')
}

function handleCreate() {
  emit('create', {
    method: formData.method,
    name: formData.name,
    path: formData.path,
    folderId: folderIdResolved.value,
    description: formData.description
  })
}

function methodButtonClass(value: ApiMethod) {
  const base = 'h-[32px] flex-1 rounded-[10px] border text-[12px] font-medium leading-[16px]'
  const isActive = formData.method === value

  if (value === 'GET') {
    if (isActive) return `${base} bg-[#00A63E] border-[#00A63E] text-white`
    return `${base} bg-white border-black/10 text-[#00A63E]`
  }
  if (value === 'POST') {
    if (isActive) return `${base} bg-[#155DFC] border-[#155DFC] text-white`
    return `${base} bg-white border-black/10 text-[#155DFC]`
  }
  if (value === 'PUT') {
    if (isActive) return `${base} bg-[#D08700] border-[#D08700] text-white`
    return `${base} bg-white border-[#FFDF20] text-[#D08700]`
  }
  if (value === 'PATCH') {
    if (isActive) return `${base} bg-[#F54900] border-[#F54900] text-white`
    return `${base} bg-white border-[#FFB86A] text-[#F54900]`
  }
  if (isActive) return `${base} bg-[#E7000B] border-[#E7000B] text-white`
  return `${base} bg-white border-[#FFA2A2] text-[#E7000B]`
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-black/40" type="button" aria-label="Close" @click="handleClose" />

    <div class="relative max-h-[calc(100vh-32px)] w-full max-w-[calc(100vw-32px)] overflow-hidden rounded-[16px] border border-black/10 bg-white shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] sm:h-[547.33px] sm:w-[512px] sm:max-h-[547.33px] sm:max-w-[512px]">
      <div class="flex h-[60.67px] items-center justify-between border-b border-black/10 px-[24px]">
        <div class="flex items-center gap-[10px]">
          <div class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px] bg-[#DBEAFE]">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path
                d="M5.25 4.08333H3.5C3.19058 4.08333 2.89383 4.20625 2.67504 4.42504C2.45625 4.64383 2.33333 4.94058 2.33333 5.25V10.5C2.33333 10.8094 2.45625 11.1062 2.67504 11.325C2.89383 11.5437 3.19058 11.6667 3.5 11.6667H10.5C10.8094 11.6667 11.1062 11.5437 11.325 11.325C11.5437 11.1062 11.6667 10.8094 11.6667 10.5V5.25C11.6667 4.94058 11.5437 4.64383 11.325 4.42504C11.1062 4.20625 10.8094 4.08333 10.5 4.08333H8.75"
                stroke="#155DFC"
                stroke-width="1.16667"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path d="M5.83333 2.33333H8.16667" stroke="#155DFC" stroke-width="1.16667" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M7 2.33333V4.08333" stroke="#155DFC" stroke-width="1.16667" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div class="text-[14px] font-semibold leading-[20px] text-[#0A0A0A]">新建接口· {{ collectionName }}</div>
        </div>

        <button type="button" class="flex h-[28px] w-[28px] items-center justify-center rounded-[10px]" aria-label="Close" @click="handleClose">
          <img :src="modalClose28" alt="" class="h-[28px] w-[28px]" />
        </button>
      </div>

      <div class="flex max-h-[calc(100vh-32px-60.67px)] flex-col gap-[16px] overflow-auto px-[24px] pt-[24px] sm:h-[calc(547.33px-60.67px)] sm:max-h-none">
        <div class="flex flex-col gap-[8px]">
          <div class="flex items-center gap-[6px]">
            <div class="h-[12px] w-[12px]">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M4 1.5H8" stroke="#717182" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M3 3.5H9" stroke="#717182" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M2.5 5.5H9.5" stroke="#717182" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">请求方法</span>
          </div>

          <div class="flex h-[32px] w-full gap-[8px]">
            <button type="button" class="text-[12px] font-medium leading-[16px]" :class="methodButtonClass('GET')" style="font-family: Consolas" @click="formData.method = 'GET'">
              GET
            </button>
            <button type="button" class="text-[12px] font-medium leading-[16px]" :class="methodButtonClass('POST')" style="font-family: Consolas" @click="formData.method = 'POST'">
              POST
            </button>
            <button type="button" class="text-[12px] font-medium leading-[16px]" :class="methodButtonClass('PUT')" style="font-family: Consolas" @click="formData.method = 'PUT'">
              PUT
            </button>
            <button type="button" class="text-[12px] font-medium leading-[16px]" :class="methodButtonClass('PATCH')" style="font-family: Consolas" @click="formData.method = 'PATCH'">
              PATCH
            </button>
            <button type="button" class="text-[12px] font-medium leading-[16px]" :class="methodButtonClass('DELETE')" style="font-family: Consolas" @click="formData.method = 'DELETE'">
              DELETE
            </button>
          </div>
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="relative h-[16px]">
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">接口名称</span>
            <span class="ml-[4px] text-[12px] font-medium leading-[16px] text-[#FB2C36]">*</span>
          </div>
          <input
            v-model="formData.name"
            class="h-[36px] w-full rounded-[10px] border border-black/10 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="例：创建用户"
            type="text"
          />
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="flex items-center gap-[6px]">
            <div class="h-[12px] w-[12px]">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M1 6H11" stroke="#717182" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M6 1V11" stroke="#717182" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">URL 路径</span>
            <span class="ml-[4px] text-[12px] font-medium leading-[16px] text-[#FB2C36]">*</span>
          </div>

          <div class="flex h-[36px] w-full overflow-hidden rounded-[10px] border border-black/10 bg-white">
            <div class="flex h-full items-center border-r border-black/10 bg-[rgba(236,236,240,0.4)] px-[12px] text-[12px] leading-[16px] text-[#717182]">
              /api
            </div>
            <input
              v-model="formData.path"
              class="h-full min-w-0 flex-1 bg-white px-[12px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
              style="font-family: Consolas"
              type="text"
            />
          </div>
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="flex items-center gap-[6px]">
            <div class="h-[12px] w-[12px]">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M2 4.5H10" stroke="#717182" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M3 3L2 4.5L3 6" stroke="#717182" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">所属文件夹</span>
          </div>

          <div class="relative h-[36px] w-full rounded-[10px] border border-black/10 bg-white">
            <select
              v-model="formData.folderId"
              class="h-full w-full appearance-none rounded-[10px] bg-transparent px-[12px] pr-[32px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            >
              <option v-for="f in folders" :key="f.id" :value="f.id">{{ f.name }}</option>
            </select>
            <img :src="filterChevron" alt="" class="pointer-events-none absolute right-[12px] top-[12px] h-[12px] w-[12px]" />
          </div>
        </div>

        <div class="flex flex-col gap-[6px]">
          <div class="flex items-center gap-[6px]">
            <img :src="modalDescIcon" alt="" class="h-[12px] w-[12px]" />
            <span class="text-[12px] font-medium leading-[16px] text-[#0A0A0A]">描述</span>
            <span class="text-[12px] leading-[16px] text-[#717182]">（可选）</span>
          </div>
          <textarea
            v-model="formData.description"
            class="h-[63.33px] w-full resize-none rounded-[10px] border border-black/10 bg-white px-[12px] py-[8px] text-[14px] leading-[20px] text-[#0A0A0A] outline-none"
            placeholder="描述该接口的功能..."
          />
        </div>

        <div class="flex items-center justify-end gap-[8px] border-t border-black/10 pt-[16px]">
          <button
            type="button"
            class="h-[32px] w-[61.33px] rounded-[10px] border border-black/10 bg-white text-[14px] font-medium leading-[20px] text-[#717182]"
            @click="handleClose"
          >
            取消
          </button>
          <button
            type="button"
            class="relative h-[32px] w-[115px] rounded-[10px] bg-[#155DFC] text-[14px] font-medium leading-[20px] text-white"
            @click="handleCreate"
          >
            <img :src="modalCreateIcon" alt="" class="absolute left-[20px] top-1/2 -translate-y-1/2 h-[13px] w-[13px]" />
            <span class="absolute left-[39px] top-[6.33px]">创建接口</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
