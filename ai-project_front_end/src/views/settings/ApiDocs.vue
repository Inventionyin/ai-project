<script setup lang="ts">
const apiDocsUrl = '/api/docs'
</script>

<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-[20px] font-semibold">API 文档</h1>
      <p class="mt-1 text-[14px] text-[#717182]">平台 API 接口文档</p>
    </div>
    <div class="rounded-[10px] border border-black/10 p-6">
      <p class="text-[14px] text-[#0A0A0A]">
        API 文档由 FastAPI 自动生成，访问
        <a :href="apiDocsUrl" target="_blank" class="text-[#155DFC] underline">/api/docs</a>
        查看 Swagger UI。
      </p>
      <p class="mt-4 text-[14px] text-[#717182]">
        或访问 <a href="/api/redoc" target="_blank" class="text-[#155DFC] underline">/api/redoc</a> 查看 ReDoc 格式文档。
      </p>
      <div class="mt-6">
        <h2 class="text-[16px] font-medium mb-3">主要 API 模块</h2>
        <div class="grid gap-3 sm:grid-cols-2">
          <div class="rounded border border-black/10 p-3">
            <h3 class="text-[13px] font-medium">认证</h3>
            <p class="text-[12px] text-[#717182]">/api/v1/auth/*</p>
          </div>
          <div class="rounded border border-black/10 p-3">
            <h3 class="text-[13px] font-medium">项目</h3>
            <p class="text-[12px] text-[#717182]">/api/v1/projects/*</p>
          </div>
          <div class="rounded border border-black/10 p-3">
            <h3 class="text-[13px] font-medium">需求文档</h3>
            <p class="text-[12px] text-[#717182]">/api/v1/projects/{id}/requirements/*</p>
          </div>
          <div class="rounded border border-black/10 p-3">
            <h3 class="text-[13px] font-medium">测试用例</h3>
            <p class="text-[12px] text-[#717182]">/api/v1/projects/{id}/testcases/*</p>
          </div>
          <div class="rounded border border-black/10 p-3">
            <h3 class="text-[13px] font-medium">接口集合</h3>
            <p class="text-[12px] text-[#717182]">/api/v1/collections/*</p>
          </div>
          <div class="rounded border border-black/10 p-3">
            <h3 class="text-[13px] font-medium">运行与报告</h3>
            <p class="text-[12px] text-[#717182]">/api/v1/runs/*</p>
          </div>
          <div class="rounded border border-black/10 p-3">
            <h3 class="text-[13px] font-medium">缺陷管理</h3>
            <p class="text-[12px] text-[#717182]">/api/v1/projects/{id}/defects/*</p>
          </div>
          <div class="rounded border border-black/10 p-3">
            <h3 class="text-[13px] font-medium">知识沉淀</h3>
            <p class="text-[12px] text-[#717182]">/api/v1/projects/{id}/knowledge/*</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
