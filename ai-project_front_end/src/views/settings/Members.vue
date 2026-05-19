<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchMembers, addMember, updateMemberRole, removeMember, searchUsers, type MemberListItem, type UserSuggestion } from '@/lib/api/members'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || route.params.id || '').trim())

const members = ref<MemberListItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const success = ref('')

// Add member
const showAddModal = ref(false)
const searchQuery = ref('')
const searchResults = ref<UserSuggestion[]>([])
const selectedUser = ref<UserSuggestion | null>(null)
const newRole = ref('VIEWER')
const adding = ref(false)

// Edit role
const editingId = ref('')
const editRole = ref('')

const roleOptions = ['OWNER', 'ADMIN', 'EDITOR', 'VIEWER']

const roleLabels: Record<string, string> = {
  OWNER: '所有者',
  ADMIN: '管理员',
  EDITOR: '编辑者',
  VIEWER: '查看者',
}

const roleColors: Record<string, string> = {
  OWNER: 'bg-purple-100 text-purple-700',
  ADMIN: 'bg-blue-100 text-blue-700',
  EDITOR: 'bg-green-100 text-green-700',
  VIEWER: 'bg-gray-100 text-gray-700',
}

async function loadMembers() {
  if (!projectId.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await fetchMembers(projectId.value)
    members.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载成员失败'
  } finally {
    loading.value = false
  }
}

async function handleSearchUsers() {
  if (!searchQuery.value.trim() || !projectId.value) {
    searchResults.value = []
    return
  }
  try {
    searchResults.value = await searchUsers(projectId.value, searchQuery.value)
  } catch {
    searchResults.value = []
  }
}

function selectUser(user: UserSuggestion) {
  selectedUser.value = user
  searchQuery.value = user.name || user.email
  searchResults.value = []
}

async function handleAddMember() {
  if (!selectedUser.value || !projectId.value) return
  adding.value = true
  error.value = ''
  success.value = ''
  try {
    await addMember(projectId.value, selectedUser.value.id, newRole.value)
    success.value = `已添加成员：${selectedUser.value.name || selectedUser.value.email}`
    showAddModal.value = false
    selectedUser.value = null
    searchQuery.value = ''
    newRole.value = 'VIEWER'
    await loadMembers()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '添加成员失败'
  } finally {
    adding.value = false
  }
}

async function handleRoleChange(member: MemberListItem, newRoleValue: string) {
  if (!projectId.value) return
  try {
    await updateMemberRole(projectId.value, member.id, newRoleValue)
    member.role = newRoleValue
    editingId.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : '更新角色失败'
  }
}

async function handleRemove(member: MemberListItem) {
  if (!projectId.value || !confirm(`确定移除成员 ${member.userName || member.userEmail}？`)) return
  try {
    await removeMember(projectId.value, member.id)
    success.value = '已移除成员'
    await loadMembers()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '移除成员失败'
  }
}

function startEdit(member: MemberListItem) {
  editingId.value = member.id
  editRole.value = member.role
}

function cancelEdit() {
  editingId.value = ''
}

onMounted(loadMembers)
watch(projectId, loadMembers)
</script>

<template>
  <div class="p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-[20px] font-semibold text-[#0A0A0A]">成员管理</h1>
        <p class="mt-1 text-[14px] text-[#717182]">管理项目成员和角色权限（共 {{ total }} 人）</p>
      </div>
      <button
        type="button"
        class="rounded-[8px] bg-[#155DFC] px-4 py-2 text-[14px] font-medium text-white hover:bg-blue-700"
        @click="showAddModal = true"
      >
        添加成员
      </button>
    </div>

    <div v-if="error" class="mb-4 rounded-[8px] bg-red-50 p-3 text-[13px] text-red-600">{{ error }}</div>
    <div v-if="success" class="mb-4 rounded-[8px] bg-green-50 p-3 text-[13px] text-green-600">{{ success }}</div>

    <div v-if="loading" class="py-8 text-center text-[14px] text-[#717182]">加载中...</div>

    <div v-else class="overflow-hidden rounded-[10px] border border-black/10">
      <table class="w-full">
        <thead>
          <tr class="border-b border-black/10 bg-[#F9FAFB]">
            <th class="px-4 py-3 text-left text-[12px] font-medium text-[#717182]">成员</th>
            <th class="px-4 py-3 text-left text-[12px] font-medium text-[#717182]">邮箱</th>
            <th class="px-4 py-3 text-left text-[12px] font-medium text-[#717182]">角色</th>
            <th class="px-4 py-3 text-right text-[12px] font-medium text-[#717182]">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="member in members" :key="member.id" class="border-b border-black/5 hover:bg-[#F9FAFB]">
            <td class="px-4 py-3 text-[14px] text-[#0A0A0A]">{{ member.userName || '-' }}</td>
            <td class="px-4 py-3 text-[13px] text-[#717182]">{{ member.userEmail || '-' }}</td>
            <td class="px-4 py-3">
              <div v-if="editingId === member.id" class="flex items-center gap-2">
                <select v-model="editRole" class="rounded border border-black/10 px-2 py-1 text-[12px]">
                  <option v-for="r in roleOptions" :key="r" :value="r">{{ roleLabels[r] }}</option>
                </select>
                <button class="text-[12px] text-[#155DFC]" @click="handleRoleChange(member, editRole)">保存</button>
                <button class="text-[12px] text-[#717182]" @click="cancelEdit">取消</button>
              </div>
              <span
                v-else
                class="inline-block cursor-pointer rounded-full px-2 py-0.5 text-[12px] font-medium"
                :class="roleColors[member.role] || 'bg-gray-100 text-gray-700'"
                @click="startEdit(member)"
              >
                {{ roleLabels[member.role] || member.role }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button class="text-[12px] text-red-500 hover:text-red-700" @click="handleRemove(member)">移除</button>
            </td>
          </tr>
          <tr v-if="members.length === 0">
            <td colspan="4" class="px-4 py-8 text-center text-[14px] text-[#717182]">暂无成员</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add Member Modal -->
    <div v-if="showAddModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div class="w-[420px] rounded-[12px] bg-white p-6 shadow-lg">
        <h2 class="mb-4 text-[16px] font-semibold text-[#0A0A0A]">添加成员</h2>

        <div class="mb-3">
          <label class="mb-1 block text-[12px] font-medium text-[#717182]">搜索用户</label>
          <input
            v-model="searchQuery"
            type="text"
            class="w-full rounded-[6px] border border-black/10 px-3 py-2 text-[13px] outline-none focus:border-[#155DFC]"
            placeholder="输入姓名或邮箱搜索"
            @input="handleSearchUsers"
          />
          <div v-if="searchResults.length > 0" class="mt-1 max-h-[120px] overflow-auto rounded border border-black/10 bg-white">
            <button
              v-for="u in searchResults"
              :key="u.id"
              type="button"
              class="block w-full px-3 py-2 text-left text-[13px] hover:bg-[#F3F4F6]"
              @click="selectUser(u)"
            >
              {{ u.name || u.email }} <span class="text-[#717182]">{{ u.email }}</span>
            </button>
          </div>
        </div>

        <div class="mb-4">
          <label class="mb-1 block text-[12px] font-medium text-[#717182]">角色</label>
          <select v-model="newRole" class="w-full rounded-[6px] border border-black/10 px-3 py-2 text-[13px]">
            <option v-for="r in roleOptions" :key="r" :value="r">{{ roleLabels[r] }}</option>
          </select>
        </div>

        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="rounded-[6px] border border-black/10 px-4 py-2 text-[13px] text-[#717182] hover:bg-[#F3F4F6]"
            @click="showAddModal = false; selectedUser = null; searchQuery = ''"
          >
            取消
          </button>
          <button
            type="button"
            class="rounded-[6px] bg-[#155DFC] px-4 py-2 text-[13px] font-medium text-white disabled:opacity-50"
            :disabled="!selectedUser || adding"
            @click="handleAddMember"
          >
            {{ adding ? '添加中...' : '确认添加' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
