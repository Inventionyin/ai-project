<script setup lang="ts">
import { computed, ref } from 'vue'
import suiteDetailSearch from '@/assets/figma/ai-testing-platform/suite-detail-search.svg'

type PoolCase = {
  title: string
  typeLabel: string
  priority: string
}

const props = defineProps<{
  cases: PoolCase[]
  selectedIndex: number | null
}>()

const emit = defineEmits<{
  (e: 'select', index: number): void
  (e: 'add', index: number): void
}>()

const keyword = ref('')

const filteredCases = computed(() => {
  const k = keyword.value.trim()
  if (!k) return props.cases
  return props.cases.filter((item) => item.title.includes(k))
})

const hoverIndex = ref<number | null>(null)
</script>

<template>
  <section class="flex w-full flex-col bg-[rgba(236,236,240,0.2)] md:w-[288px] md:border-r-[0.6667px] md:border-black/10">
    <div class="flex flex-col gap-[8px] border-b-[0.6667px] border-black/10 px-[12px] pt-[12px] pb-[0.67px]">
      <div class="text-[12px] font-semibold leading-[16px] text-[#717182]">用例池</div>

      <div class="relative h-[32px] w-full">
        <img :src="suiteDetailSearch" alt="" class="absolute left-[10px] top-[9.5px] h-[13px] w-[13px]" />
        <input
          v-model="keyword"
          class="h-[32px] w-full rounded-[10px] border-[0.6667px] border-black/10 bg-white pl-[28px] pr-[8px] text-[12px] leading-[16px] text-[#0A0A0A] outline-none placeholder:text-[#0A0A0A]"
          placeholder="搜索用例..."
        />
      </div>
    </div>

    <div class="flex flex-1 flex-col gap-[4px] px-[8px] pt-[8px] pb-0">
      <div
        v-for="(item, idx) in filteredCases"
        :key="`${item.title}-${idx}`"
        class="group relative flex cursor-pointer items-center justify-between rounded-[10px] border-[0.6667px] border-black/10 bg-white px-[8px] pr-[40px] py-[8px] hover:border-[#155DFC]/50"
        @mouseenter="hoverIndex = props.cases.indexOf(item)"
        @mouseleave="hoverIndex = null"
        @click="emit('select', props.cases.indexOf(item))"
      >
        <div class="flex min-w-0 flex-1 flex-col gap-[2px]">
          <div class="truncate text-[12px] leading-[16px] text-[#0A0A0A]">{{ item.title }}</div>
          <div class="flex items-center gap-[4px]">
            <span class="inline-flex h-[16px] items-center rounded-[4px] bg-[#DBEAFE] px-[6px] text-[12px] leading-[16px] text-[#1447E6]">
              {{ item.typeLabel }}
            </span>
            <span class="text-[12px] leading-[16px] text-[#717182]">{{ item.priority }}</span>
          </div>
        </div>
        <button
          v-show="props.selectedIndex === props.cases.indexOf(item) || hoverIndex === props.cases.indexOf(item)"
          type="button"
          class="absolute right-[6px] top-1/2 h-[32px] w-[32px] -translate-y-1/2 rounded-[8px] bg-[#155DFC] text-white opacity-0 shadow-sm transition-all duration-200 ease-out group-hover:opacity-100 hover:scale-110 active:scale-95"
          @click.stop="emit('add', props.cases.indexOf(item))"
        >
          <span class="block text-[20px] leading-[32px]">+</span>
        </button>
      </div>
    </div>
  </section>
</template>
