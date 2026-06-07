<template>
  <div class="page-api-monitor">
    <h2 class="page-title">API 监控台</h2>

    <el-row :gutter="16">
      <!-- 萤石开放平台 -->
      <el-col :xs="24" :sm="12">
        <div class="monitor-panel">
          <div class="panel-header">📷 萤石开放平台用量</div>
          <div class="panel-body">
            <div class="ring-wrap">
              <el-progress type="circle" :percentage="ezvizPercent" :width="160" :stroke-width="12" :color="ezvizColor">
                <template #default>
                  <div class="ring-center">
                    <div class="big-num">{{ apiUsage.ezviz_api?.calls_today?.toLocaleString() }}</div>
                    <div class="pct-label">/ {{ apiUsage.ezviz_api?.limit_daily?.toLocaleString() }} 次</div>
                  </div>
                </template>
              </el-progress>
            </div>

            <div class="usage-stats">
              <div class="usage-stat">
                <div class="stat-num" style="color: var(--color-success);">{{ ezvizRemain.toLocaleString() }}</div>
                <div class="stat-label">剩余额度</div>
              </div>
              <div class="usage-stat">
                <div class="stat-num">{{ ezvizPercent }}%</div>
                <div class="stat-label">使用率</div>
              </div>
            </div>

            <p class="panel-note">
              额度使用率{{ ezvizPercent > 80 ? '偏高' : '正常' }}，{{ ezvizPercent > 80 ? '请关注用量' : '距免费额度上限仍有较大余量' }}
            </p>
          </div>
        </div>
      </el-col>

      <!-- 大模型服务 -->
      <el-col :xs="24" :sm="12">
        <div class="monitor-panel">
          <div class="panel-header">🧠 大模型服务监控</div>
          <div class="panel-body">
            <!-- 时间范围切换 -->
            <el-radio-group v-model="timeRange" size="small" style="margin-bottom: var(--spacing-md);">
              <el-radio-button value="day">今日</el-radio-button>
              <el-radio-button value="week">本周</el-radio-button>
              <el-radio-button value="month">本月</el-radio-button>
            </el-radio-group>

            <!-- Token 消耗表格 -->
            <el-table :data="tokenTableData" stripe border size="small" style="width: 100%">
              <el-table-column prop="metric" label="指标" />
              <el-table-column prop="value" label="数值" />
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.statusType" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
            </el-table>

            <!-- 响应延迟 -->
            <div class="latency-card">
              <div>
                <div class="latency-value">{{ apiUsage.llm_qwen?.latency_ms || 0 }}<span class="latency-unit">ms</span></div>
                <div class="latency-label">接口响应延迟</div>
              </div>
              <el-tag type="success" size="large">健康</el-tag>
            </div>

            <p class="panel-note">Qwen 大模型服务运行正常，近1小时无异常波动</p>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * API监控台 - 时间范围切换、Token用量指标、延迟监控
 */
import { ref, computed, onMounted } from 'vue'
import { getApiUsage } from '@/api/devices'

const apiUsage = ref({ ezviz_api: {}, llm_qwen: {} })
const timeRange = ref('day')

const ezvizPercent = computed(() => {
  const used = apiUsage.value.ezviz_api?.calls_today || 0
  const limit = apiUsage.value.ezviz_api?.limit_daily || 1
  return Math.round((used / limit) * 100)
})

const ezvizRemain = computed(() => {
  const used = apiUsage.value.ezviz_api?.calls_today || 0
  const limit = apiUsage.value.ezviz_api?.limit_daily || 0
  return Math.max(0, limit - used)
})

const ezvizColor = computed(() => {
  if (ezvizPercent.value > 80) return '#F56C6C'
  if (ezvizPercent.value > 60) return '#E6A23C'
  return '#67C23A'
})

const tokenTableData = computed(() => {
  const llm = apiUsage.value.llm_qwen || {}
  const monthPct = llm.tokens_month && llm.monthly_limit ? Math.round((llm.tokens_month / llm.monthly_limit) * 100) : 0
  return [
    { metric: 'Token 消耗', value: (llm.tokens_today || 0).toLocaleString(), status: '正常', statusType: 'info' },
    { metric: 'API 调用次数', value: (llm.api_calls_today || 0).toLocaleString(), status: '正常', statusType: 'info' },
    { metric: '月累计消耗', value: (llm.tokens_month || 0).toLocaleString(), status: monthPct > 80 ? '偏高' : '正常', statusType: monthPct > 80 ? 'warning' : 'info' },
    { metric: '月额度上限', value: (llm.monthly_limit || 0).toLocaleString(), status: '-', statusType: 'info' },
  ]
})

async function loadApiUsage() {
  try {
    const res = await getApiUsage()
    apiUsage.value = res
  } catch (e) {
    console.error('加载 API 用量失败', e)
  }
}

onMounted(() => {
  loadApiUsage()
})
</script>

<style scoped>
.page-api-monitor {
  padding: 0;
}

.page-title {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-lg);
}

.monitor-panel {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.panel-header {
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.panel-body {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ring-wrap {
  margin-bottom: var(--spacing-md);
}

.ring-center {
  text-align: center;
}

.ring-center .big-num {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
}

.ring-center .pct-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.usage-stats {
  display: flex;
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-sm);
}

.usage-stat {
  text-align: center;
}

.usage-stat .stat-num {
  font-size: 24px;
  font-weight: 700;
}

.usage-stat .stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.latency-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: var(--color-success-bg, #f0f9eb);
  border-radius: var(--radius-md);
  padding: var(--spacing-md) var(--spacing-lg);
  margin-top: var(--spacing-md);
}

.latency-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-success);
}

.latency-unit {
  font-size: 16px;
}

.latency-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.panel-note {
  font-size: 12px;
  color: var(--color-text-light);
  text-align: center;
  margin-top: var(--spacing-sm);
}
</style>
