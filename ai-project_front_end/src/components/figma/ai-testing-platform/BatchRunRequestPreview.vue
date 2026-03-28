<script setup lang="ts">
import submitIcon from '@/assets/figma/ai-testing-platform/batch-run-info-icon.svg'

defineProps<{
  concurrency: number
  stopOnFailure: boolean
  idempotencyKey: string
}>()
</script>

<template>
  <div class="relative h-[129.33px] w-full rounded-[14px] border border-black/10 bg-[rgba(236,236,240,0.3)]">
    <div class="absolute left-[12.67px] top-[12.67px] h-[20px] w-[590px]">
      <img :src="submitIcon" alt="" class="absolute left-0 top-[4px] h-[12px] w-[12px]" />
      <div class="absolute left-[18px] top-[2px] h-[16px] w-[52px] text-[12px] leading-[16px] text-[#717182]">
        将提交至
      </div>
      <div class="absolute left-[72px] top-0 h-[20px] w-[203.33px] rounded-[4px] bg-[#ECECF0]">
        <div class="absolute left-[6px] top-[1.67px] text-[12px] leading-[16px] text-[#0A0A0A]" style="font-family: Consolas">
          POST /api/runs/from-testcases
        </div>
      </div>
    </div>

    <div class="absolute left-[12.67px] top-[40.67px] flex h-[16px] w-[590px] items-center gap-[8px]">
      <div class="h-[16px] w-[112px] text-[12px] leading-[16px] text-[#717182]">runMode</div>
      <div class="text-[12px] leading-[16px] text-[#0A0A0A]" style="font-family: Consolas">TESTCASES</div>
    </div>

    <div class="absolute left-[12.67px] top-[60.67px] flex h-[16px] w-[590px] items-center gap-[8px]">
      <div class="h-[16px] w-[112px] text-[12px] leading-[16px] text-[#717182]">concurrency</div>
      <div class="text-[12px] leading-[16px] text-[#0A0A0A]" style="font-family: Consolas">{{ concurrency }}</div>
    </div>

    <div class="absolute left-[12.67px] top-[80.67px] flex h-[16px] w-[590px] items-center gap-[8px]">
      <div class="h-[16px] w-[112px] text-[12px] leading-[16px] text-[#717182]">stopOnFailure</div>
      <div class="text-[12px] leading-[16px] text-[#0A0A0A]" style="font-family: Consolas">
        {{ stopOnFailure ? 'true' : 'false' }}
      </div>
    </div>

    <div class="absolute left-[12.67px] top-[100.67px] flex h-[16px] w-[590px] items-center gap-[8px]">
      <div class="h-[16px] w-[112px] text-[12px] leading-[16px] text-[#717182]">Idempotency-Key</div>
      <div class="text-[12px] leading-[16px] text-[#0A0A0A]" style="font-family: Consolas">{{ idempotencyKey }}</div>
    </div>
  </div>
</template>
