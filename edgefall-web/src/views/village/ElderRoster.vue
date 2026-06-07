<template>
  <div class="page-elder-roster">
    <div class="page-title-row">
      <h2>辖区老人名册</h2>
    </div>

    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="按姓名或住址搜索..."
        clearable
        @input="handleSearch"
        style="max-width: 360px"
      />
    </div>

    <el-table
      :data="filteredList"
      stripe
      border
      style="width: 100%"
      @row-click="handleRowClick"
      class="roster-table"
    >
      <el-table-column prop="name" label="姓名" width="100">
        <template #default="{ row }">
          <strong>{{ row.name }}</strong>
        </template>
      </el-table-column>
      <el-table-column prop="age" label="年龄" width="70" />
      <el-table-column prop="gender" label="性别" width="70" />
      <el-table-column prop="address" label="住址" min-width="120" />
      <el-table-column prop="device_sn" label="手环编号" width="100" />
      <el-table-column prop="gateway_sn" label="网关编号" width="100" />
      <el-table-column prop="emergency_contact" label="家属电话" width="120" />
      <el-table-column label="风险标签" min-width="200">
        <template #default="{ row }">
          <el-tag
            v-for="tag in row.risk_tags"
            :key="tag"
            :type="tagType(tag)"
            size="small"
            style="margin-right: 4px"
          >
            {{ tag }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalCount"
        layout="prev, pager, next"
        @current-change="loadElders"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * 老人名册 - 搜索筛选、分页、风险标签、行点击跳转详情
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getElders } from '@/api/elders'

const router = useRouter()

const elders = ref([])
const keyword = ref('')
const currentPage = ref(1)
const pageSize = 10
const totalCount = ref(0)

const filteredList = computed(() => {
  if (!keyword.value) return elders.value
  const kw = keyword.value.toLowerCase()
  return elders.value.filter(e =>
    e.name.toLowerCase().includes(kw) || e.address.toLowerCase().includes(kw)
  )
})

function tagType(tag) {
  if (tag.includes('跌倒') || tag.includes('情绪低落')) return 'danger'
  if (tag.includes('不稳') || tag.includes('下降') || tag.includes('减少')) return 'warning'
  return 'success'
}

let searchTimer = null
function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadElders()
  }, 300)
}

async function loadElders() {
  try {
    const res = await getElders({ page: currentPage.value, size: pageSize, keyword: keyword.value })
    elders.value = res.items || []
    totalCount.value = res.total || elders.value.length
  } catch (e) {
    console.error('加载老人列表失败', e)
  }
}

function handleRowClick(row) {
  router.push(`/village/elder-detail/${row.elder_id}`)
}

onMounted(() => {
  loadElders()
})
</script>

<style scoped>
.page-elder-roster {
  padding: 0;
}

.page-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.page-title-row h2 {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.search-bar {
  margin-bottom: var(--spacing-md);
  display: flex;
  gap: var(--spacing-sm);
}

.roster-table {
  cursor: pointer;
}

.roster-table :deep(.el-table__row) {
  cursor: pointer;
}

.roster-table :deep(.el-table__row:hover) {
  background: var(--color-primary-light);
  background: rgba(64, 158, 255, 0.04);
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-lg);
}
</style>
