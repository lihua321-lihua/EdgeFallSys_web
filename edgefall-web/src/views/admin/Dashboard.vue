<template>
  <div class="page-dashboard">
    <h2 class="page-title">运维仪表盘</h2>

    <!-- 设备概览 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <span class="stat-label">设备总数</span>
          <span class="stat-value primary">{{ deviceStats.total }}</span>
          <span class="stat-sub">台</span>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <span class="stat-label">在线设备</span>
          <span class="stat-value success">{{ deviceStats.online }}</span>
          <span class="stat-sub">台</span>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <span class="stat-label">离线设备</span>
          <span class="stat-value danger">{{ deviceStats.offline }}</span>
          <span class="stat-sub">台</span>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <span class="stat-label">低电量</span>
          <span class="stat-value warning">{{ deviceStats.lowBattery }}</span>
          <span class="stat-sub">台</span>
        </div>
      </el-col>
    </el-row>

    <!-- API 概览 -->
    <el-row :gutter="16" class="api-row">
      <el-col :xs="24" :sm="12">
        <div class="api-card">
          <h3>萤石 API 今日调用</h3>
          <el-progress :percentage="ezvizPercent" :stroke-width="12" />
          <div class="api-detail">
            <span>已用：{{ apiUsage.ezviz_api?.calls_today?.toLocaleString() }} 次</span>
            <span>总额度：{{ apiUsage.ezviz_api?.limit_daily?.toLocaleString() }} 次 ({{ ezvizPercent }}%)</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12">
        <div class="api-card">
          <h3>大模型 Token 消耗</h3>
          <el-progress :percentage="llmPercent" :stroke-width="12" :color="llmPercent > 80 ? '#F56C6C' : '#E6A23C'" />
          <div class="api-detail">
            <span>今日：{{ apiUsage.llm_qwen?.tokens_today?.toLocaleString() }}</span>
            <span>本月：{{ apiUsage.llm_qwen?.tokens_month?.toLocaleString() }} / {{ apiUsage.llm_qwen?.monthly_limit?.toLocaleString() }} ({{ llmPercent }}%)</span>
          </div>
          <el-alert v-if="llmPercent > 80" title="Token 用量超过 80%，请关注" type="warning" :closable="false" show-icon style="margin-top: 8px" />
        </div>
      </el-col>
    </el-row>

    <!-- 最近告警 -->
    <div class="recent-alerts">
      <h3>最近跨村告警</h3>
      <el-table :data="recentAlerts" stripe border style="width: 100%">
        <el-table-column prop="time" label="时间" width="100" />
        <el-table-column prop="village" label="村庄" width="100" />
        <el-table-column prop="elder" label="老人" width="100" />
        <el-table-column label="告警类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.type === '跌倒报警' ? 'danger' : 'warning'" size="small">
              {{ row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
/**
 * 管理仪表盘 - 统计卡片、API用量、跨村告警、阈值预警
 */
import { ref, computed, onMounted } from 'vue'
import { getDevices } from '@/api/devices'
import { getApiUsage } from '@/api/devices'

const deviceStats = ref({ total: 0, online: 0, offline: 0, lowBattery: 0 })
const apiUsage = ref({ ezviz_api: {}, llm_qwen: {} })

const recentAlerts = ref([
  { time: '14:32', village: '桂花村', elder: '王大爷', type: '跌倒报警', status: '待处理' },
  { time: '13:58', village: '桂花村', elder: '李奶奶', type: '跌倒报警', status: '待处理' },
  { time: '11:20', village: '杨柳村', elder: '刘爷爷', type: '设备离线', status: '已通知' },
  { time: '09:15', village: '石门村', elder: '陈奶奶', type: '低电量', status: '已通知' },
  { time: '08:05', village: '桃花村', elder: '周大爷', type: '跌倒报警', status: '已处理' },
])

const ezvizPercent = computed(() => {
  const used = apiUsage.value.ezviz_api?.calls_today || 0
  const limit = apiUsage.value.ezviz_api?.limit_daily || 1
  return Math.round((used / limit) * 100)
})

const llmPercent = computed(() => {
  const used = apiUsage.value.llm_qwen?.tokens_month || 0
  const limit = apiUsage.value.llm_qwen?.monthly_limit || 1
  return Math.round((used / limit) * 100)
})

async function loadDashboard() {
  try {
    const [devRes, apiRes] = await Promise.allSettled([
      getDevices(),
      getApiUsage(),
    ])
    if (devRes.status === 'fulfilled' && devRes.value?.items) {
      const items = devRes.value.items
      deviceStats.value = {
        total: items.length,
        online: items.filter(d => d.is_online).length,
        offline: items.filter(d => !d.is_online).length,
        lowBattery: items.filter(d => d.battery_level < 20).length,
      }
    }
    if (apiRes.status === 'fulfilled') {
      apiUsage.value = apiRes.value
    }
  } catch (e) {
    console.error('加载仪表盘失败', e)
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.page-dashboard {
  padding: 0;
}

.page-title {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-lg);
}

/* 统计卡片 */
.stat-row {
  margin-bottom: var(--spacing-lg);
}

.stat-card {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-card);
  text-align: center;
}

.stat-card .stat-label {
  display: block;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xs);
}

.stat-card .stat-value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-card .stat-value.primary { color: var(--color-primary); }
.stat-card .stat-value.success { color: var(--color-success); }
.stat-card .stat-value.danger { color: var(--color-danger); }
.stat-card .stat-value.warning { color: var(--color-warning); }

.stat-card .stat-sub {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-left: 4px;
}

/* API 卡片 */
.api-row {
  margin-bottom: var(--spacing-lg);
}

.api-card {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-card);
}

.api-card h3 {
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-md);
}

.api-card .api-detail {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* 最近告警 */
.recent-alerts {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-card);
}

.recent-alerts h3 {
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-md);
}
</style>
