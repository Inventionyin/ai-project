<template>
  <div class="rounded-[12px] border border-black/10 bg-white p-4">
    <div class="flex items-center justify-between mb-3">
      <div class="text-[14px] font-semibold text-[#0A0A0A]">风险矩阵</div>
      <div class="text-[12px] text-[#717182]">共 {{ risks.length }} 个风险点</div>
    </div>

    <div v-if="risks.length === 0" class="text-[12px] text-[#717182] py-4 text-center">暂无风险点</div>

    <div v-else>
      <!-- Matrix grid -->
      <div class="grid grid-cols-4 gap-1 text-[11px]">
        <!-- Header row -->
        <div class="p-2"></div>
        <div class="p-2 text-center font-medium text-[#717182] bg-gray-50 rounded">低概率</div>
        <div class="p-2 text-center font-medium text-[#717182] bg-gray-50 rounded">中概率</div>
        <div class="p-2 text-center font-medium text-[#717182] bg-gray-50 rounded">高概率</div>

        <!-- CRITICAL row -->
        <div class="p-2 font-medium text-red-700 bg-red-50 rounded flex items-center">严重影响</div>
        <div class="p-2 min-h-[48px] rounded border border-orange-200 bg-orange-50 flex items-center justify-center">
          <span v-if="cellRisks('CRITICAL', 'LOW').length" class="text-orange-700 font-medium">{{ cellRisks('CRITICAL', 'LOW').length }}</span>
        </div>
        <div class="p-2 min-h-[48px] rounded border border-red-200 bg-red-50 flex items-center justify-center">
          <span v-if="cellRisks('CRITICAL', 'MEDIUM').length" class="text-red-700 font-medium">{{ cellRisks('CRITICAL', 'MEDIUM').length }}</span>
        </div>
        <div class="p-2 min-h-[48px] rounded border border-red-300 bg-red-100 flex items-center justify-center">
          <span v-if="cellRisks('CRITICAL', 'HIGH').length" class="text-red-800 font-bold">{{ cellRisks('CRITICAL', 'HIGH').length }}</span>
        </div>

        <!-- HIGH row -->
        <div class="p-2 font-medium text-orange-700 bg-orange-50 rounded flex items-center">高影响</div>
        <div class="p-2 min-h-[48px] rounded border border-yellow-200 bg-yellow-50 flex items-center justify-center">
          <span v-if="cellRisks('HIGH', 'LOW').length" class="text-yellow-700 font-medium">{{ cellRisks('HIGH', 'LOW').length }}</span>
        </div>
        <div class="p-2 min-h-[48px] rounded border border-orange-200 bg-orange-50 flex items-center justify-center">
          <span v-if="cellRisks('HIGH', 'MEDIUM').length" class="text-orange-700 font-medium">{{ cellRisks('HIGH', 'MEDIUM').length }}</span>
        </div>
        <div class="p-2 min-h-[48px] rounded border border-red-200 bg-red-50 flex items-center justify-center">
          <span v-if="cellRisks('HIGH', 'HIGH').length" class="text-red-700 font-medium">{{ cellRisks('HIGH', 'HIGH').length }}</span>
        </div>

        <!-- MEDIUM row -->
        <div class="p-2 font-medium text-yellow-700 bg-yellow-50 rounded flex items-center">中影响</div>
        <div class="p-2 min-h-[48px] rounded border border-green-200 bg-green-50 flex items-center justify-center">
          <span v-if="cellRisks('MEDIUM', 'LOW').length" class="text-green-700 font-medium">{{ cellRisks('MEDIUM', 'LOW').length }}</span>
        </div>
        <div class="p-2 min-h-[48px] rounded border border-yellow-200 bg-yellow-50 flex items-center justify-center">
          <span v-if="cellRisks('MEDIUM', 'MEDIUM').length" class="text-yellow-700 font-medium">{{ cellRisks('MEDIUM', 'MEDIUM').length }}</span>
        </div>
        <div class="p-2 min-h-[48px] rounded border border-orange-200 bg-orange-50 flex items-center justify-center">
          <span v-if="cellRisks('MEDIUM', 'HIGH').length" class="text-orange-700 font-medium">{{ cellRisks('MEDIUM', 'HIGH').length }}</span>
        </div>

        <!-- LOW row -->
        <div class="p-2 font-medium text-green-700 bg-green-50 rounded flex items-center">低影响</div>
        <div class="p-2 min-h-[48px] rounded border border-green-200 bg-green-50 flex items-center justify-center">
          <span v-if="cellRisks('LOW', 'LOW').length" class="text-green-700">{{ cellRisks('LOW', 'LOW').length }}</span>
        </div>
        <div class="p-2 min-h-[48px] rounded border border-green-200 bg-green-50 flex items-center justify-center">
          <span v-if="cellRisks('LOW', 'MEDIUM').length" class="text-green-700">{{ cellRisks('LOW', 'MEDIUM').length }}</span>
        </div>
        <div class="p-2 min-h-[48px] rounded border border-yellow-200 bg-yellow-50 flex items-center justify-center">
          <span v-if="cellRisks('LOW', 'HIGH').length" class="text-yellow-700">{{ cellRisks('LOW', 'HIGH').length }}</span>
        </div>
      </div>

      <!-- Risk list -->
      <div class="mt-4 space-y-1">
        <div v-for="risk in risks" :key="risk.id || risk.title" class="flex items-center gap-2 text-[12px] p-1.5 rounded border border-black/5">
          <span class="w-2 h-2 rounded-full flex-shrink-0" :class="riskDotClass(risk.level)"></span>
          <span class="truncate">{{ risk.title || risk.description || '-' }}</span>
          <span class="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded" :class="riskTagClass(risk.level)">{{ risk.level || '-' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface RiskItem {
  id?: string
  title?: string
  description?: string
  level?: string
  probability?: string
}

const props = defineProps<{ risks: RiskItem[] }>()

function normalizeLevel(level?: string): string {
  return String(level || 'MEDIUM').toUpperCase()
}

function cellRisks(impact: string, probability: string) {
  return props.risks.filter(r => {
    const rLevel = normalizeLevel(r.level)
    const rProb = normalizeLevel(r.probability)
    // Map level to impact, probability to probability
    const impactMatch = rLevel === impact
    const probMatch = rProb === probability || (!r.probability && probability === 'MEDIUM')
    return impactMatch && probMatch
  })
}

function riskDotClass(level?: string) {
  const v = normalizeLevel(level)
  if (v === 'CRITICAL') return 'bg-red-500'
  if (v === 'HIGH') return 'bg-orange-500'
  if (v === 'MEDIUM') return 'bg-yellow-500'
  return 'bg-green-500'
}

function riskTagClass(level?: string) {
  const v = normalizeLevel(level)
  if (v === 'CRITICAL') return 'bg-red-100 text-red-700'
  if (v === 'HIGH') return 'bg-orange-100 text-orange-700'
  if (v === 'MEDIUM') return 'bg-yellow-100 text-yellow-700'
  return 'bg-green-100 text-green-700'
}
</script>
