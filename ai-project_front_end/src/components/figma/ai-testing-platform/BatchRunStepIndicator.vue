<script setup lang="ts">
const props = withDefaults(defineProps<{
  activeStep?: 1 | 2 | 3
}>(), {
  activeStep: 1
})

function stepCircleClass(step: 1 | 2 | 3) {
  if (props.activeStep === step) {
    return 'bg-[#155DFC] text-white shadow-[0px_0px_0px_4px_#DBEAFE]'
  }
  if (props.activeStep > step) {
    return 'bg-[#155DFC] text-white'
  }
  return 'bg-[#ECECF0] text-[#717182]'
}

function isCompleted(step: 1 | 2 | 3) {
  return props.activeStep > step
}

function stepLabelClass(step: 1 | 2 | 3) {
  if (props.activeStep >= step) return 'text-[#0A0A0A]'
  return 'text-[#717182]'
}

function connectorClass(stepFrom: 1 | 2) {
  if (props.activeStep > stepFrom) return 'bg-[#155DFC]/30'
  return 'bg-black/10'
}
</script>

<template>
  <div class="w-full overflow-x-auto">
    <div class="flex h-[24px] w-[615.33px] items-center">
      <div class="flex h-[24px] w-[134px] items-center gap-[12px]">
        <div class="flex h-[24px] w-[78px] items-center gap-[6px]">
          <div class="flex h-[24px] w-[24px] items-center justify-center rounded-full text-[12px] font-semibold leading-[16px]" :class="stepCircleClass(1)">
            <svg
              v-if="isCompleted(1)"
              class="h-[12px] w-[12px]"
              viewBox="0 0 12 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path d="M10 3.5L5 8.5L2 5.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span v-else>1</span>
          </div>
          <div class="h-[16px] text-[12px] font-medium leading-[16px]" :class="stepLabelClass(1)">接口绑定</div>
        </div>
        <div class="h-[1px] w-[32px]" :class="connectorClass(1)"></div>
      </div>

      <div class="flex h-[24px] w-[134px] items-center gap-[12px]">
        <div class="flex h-[24px] w-[78px] items-center gap-[6px]">
          <div class="flex h-[24px] w-[24px] items-center justify-center rounded-full text-[12px] font-semibold leading-[16px]" :class="stepCircleClass(2)">
            <svg
              v-if="isCompleted(2)"
              class="h-[12px] w-[12px]"
              viewBox="0 0 12 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path d="M10 3.5L5 8.5L2 5.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span v-else>2</span>
          </div>
          <div class="h-[16px] text-[12px] font-medium leading-[16px]" :class="stepLabelClass(2)">数据绑定</div>
        </div>
        <div class="h-[1px] w-[32px]" :class="connectorClass(2)"></div>
      </div>

      <div class="flex h-[24px] w-[78px] items-center">
        <div class="flex h-[24px] w-full items-center gap-[6px]">
          <div class="flex h-[24px] w-[24px] items-center justify-center rounded-full text-[12px] font-semibold leading-[16px]" :class="stepCircleClass(3)">
            <svg
              v-if="isCompleted(3)"
              class="h-[12px] w-[12px]"
              viewBox="0 0 12 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path d="M10 3.5L5 8.5L2 5.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span v-else>3</span>
          </div>
          <div class="h-[16px] text-[12px] font-medium leading-[16px]" :class="stepLabelClass(3)">执行参数</div>
        </div>
      </div>
    </div>
  </div>
</template>
