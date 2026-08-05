<template>
  <div class="page-api-monitor">
    <h2 class="page-title">API 监控台</h2>

    <el-row :gutter="16">
      <!-- 萤石开放平台 -->
      <el-col :xs="24" :sm="12">
        <div class="monitor-panel">
          <div class="panel-header">
            📷 萤石开放平台用量
            <el-tag :type="ezvizStatusType" size="small" style="margin-left: 8px;">{{ ezvizStatusText }}</el-tag>
          </div>
          <div class="panel-body">
            <div class="ring-wrap">
              <el-progress type="circle" :percentage="ezvizPercent" :width="160" :stroke-width="12" :color="ezvizColor">
                <template #default>
                  <div class="ring-center">
                    <div class="big-num">{{ (apiUsage.ezviz_api?.calls_today || 0).toLocaleString() }}</div>
                    <div class="pct-label">/ {{ (apiUsage.ezviz_api?.limit_daily || 0).toLocaleString() }} 次</div>
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
              {{ apiUsage.ezviz_api?.status === 'active'
                ? (ezvizPercent > 80 ? '额度使用率偏高，请关注用量' : '凭证有效，距免费额度上限仍有余量')
                : '萤石凭证未配置，配置 AppKey/Secret 后显示真实调用计数' }}
            </p>
          </div>
        </div>
      </el-col>

      <!-- 大模型服务 -->
      <el-col :xs="24" :sm="12">
        <div class="monitor-panel">
          <div class="panel-header">
            🧠 大模型服务监控
            <el-tag :type="llm.qwen_configured ? 'success' : 'info'" size="small" style="margin-left: 8px;">
              {{ llm.qwen_configured ? '已配置' : '未配置' }}
            </el-tag>
          </div>
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

            <!-- 监控指标卡片 -->
            <div class="metric-cards">
              <div class="metric-card">
                <div class="metric-value">{{ llm.success_rate ?? 0 }}%</div>
                <div class="metric-label">今日成功率</div>
              </div>
              <div class="metric-card">
                <div class="metric-value" :style="{ color: (llm.error_count || 0) > 0 ? 'var(--color-danger)' : 'var(--color-success)' }">{{ llm.error_count || 0 }}</div>
                <div class="metric-label">异常次数</div>
              </div>
              <div class="metric-card">
                <div class="metric-value">{{ llm.avg_latency_ms || 0 }}<span class="metric-unit">ms</span></div>
                <div class="metric-label">平均延迟</div>
              </div>
            </div>

            <p class="panel-note">
              {{ llm.qwen_configured
                ? `Qwen 服务${(llm.success_rate ?? 0) >= 95 ? '运行正常' : '存在异常'}，今日调用 ${llm.api_calls_today || 0} 次`
                : 'DashScope API Key 未配置，大模型调用将降级返回默认文本' }}
            </p>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 趋势图表 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :xs="24" :sm="12">
        <div class="monitor-panel">
          <div class="panel-header">📈 Token 消耗趋势（近{{ trendDays }}天）</div>
          <div class="panel-body">
            <div ref="tokenChartRef" class="chart-box"></div>
            <p v-if="!tokenTrend.length" class="panel-note">暂无调用记录，触发大模型调用后显示趋势</p>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12">
        <div class="monitor-panel">
          <div class="panel-header">⏱ 响应延迟趋势（近{{ trendDays }}天）</div>
          <div class="panel-body">
            <div ref="latencyChartRef" class="chart-box"></div>
            <p v-if="!tokenTrend.length" class="panel-note">暂无调用记录，触发大模型调用后显示趋势</p>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * API监控台 - 真实数据驱动
 * 数据来源：后端 /system/api-usage（ApiUsage 表 + Redis 计数 + LlmCallLog 聚合）
 * 切换 timeRange 触发重载，echarts 绘制 token/延迟 趋势图
 */
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getApiUsage } from '@/api/devices'

const apiUsage = ref({ ezviz_api: {}, llm_qwen: {}, token_trend: [] })
const timeRange = ref('day')

const llm = computed(() => apiUsage.value.llm_qwen || {})
const tokenTrend = computed(() => apiUsage.value.token_trend || [])
const trendDays = computed(() => ({ day: 7, week: 14, month: 30 }[timeRange.value] || 7))

const tokenChartRef = ref(null)
const latencyChartRef = ref(null)
let tokenChart = null
let latencyChart = null

// 萤石
const ezvizPercent = computed(() => {
  const used = apiUsage.value.ezviz_api?.calls_today || 0
  const limit = apiUsage.value.ezviz_api?.limit_daily || 1
  return Math.min(100, Math.round((used / limit) * 100))
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
const ezvizStatusText = computed(() =>
  apiUsage.value.ezviz_api?.status === 'active' ? '已接入' : '未接入'
)
const ezvizStatusType = computed(() =>
  apiUsage.value.ezviz_api?.status === 'active' ? 'success' : 'info'
)

// Token 表格（随 timeRange 切换展示字段）
const tokenTableData = computed(() => {
  const l = llm.value
  const showTokens = timeRange.value === 'day' ? l.tokens_today : (timeRange.value === 'week' ? l.tokens_week : l.tokens_month)
  const monthPct = l.tokens_month && l.monthly_limit ? Math.round((l.tokens_month / l.monthly_limit) * 100) : 0
  return [
    { metric: `${rangeLabel()} Token`, value: (showTokens || 0).toLocaleString(), status: '正常', statusType: 'info' },
    { metric: 'API 调用次数', value: (l.api_calls_today || 0).toLocaleString(), status: '正常', statusType: 'info' },
    { metric: '月累计消耗', value: (l.tokens_month || 0).toLocaleString(), status: monthPct > 80 ? '偏高' : '正常', statusType: monthPct > 80 ? 'warning' : 'info' },
    { metric: '预估成本(¥)', value: (l.cost_estimate_cny || 0).toFixed(4), status: '-', statusType: 'info' },
  ]
})

function rangeLabel() {
  return { day: '今日', week: '本周', month: '本月' }[timeRange.value] || '今日'
}

function renderCharts() {
  const trend = tokenTrend.value
  const dates = trend.map(t => t.date.slice(5)) // MM-DD

  if (tokenChart) {
    tokenChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 16, top: 24, bottom: 28 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
      series: [{
        name: 'Token', type: 'line', smooth: true,
        data: trend.map(t => t.tokens),
        itemStyle: { color: '#409EFF' },
        areaStyle: { color: 'rgba(64,158,255,0.15)' },
      }],
    }, true)
  }
  if (latencyChart) {
    latencyChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 16, top: 24, bottom: 28 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 10 }, name: 'ms', nameTextStyle: { fontSize: 10 } },
      series: [{
        name: '延迟', type: 'line', smooth: true,
        data: trend.map(t => t.avg_latency_ms),
        itemStyle: { color: '#67C23A' },
        areaStyle: { color: 'rgba(103,194,58,0.15)' },
      }],
    }, true)
  }
}

async function loadApiUsage() {
  try {
    const res = await getApiUsage(timeRange.value)
    apiUsage.value = res
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error('加载 API 用量失败', e)
  }
}

watch(timeRange, () => loadApiUsage())

onMounted(() => {
  tokenChart = echarts.init(tokenChartRef.value)
  latencyChart = echarts.init(latencyChartRef.value)
  loadApiUsage()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  tokenChart?.dispose()
  latencyChart?.dispose()
})

function handleResize() {
  tokenChart?.resize()
  latencyChart?.resize()
}
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
  display: flex;
  align-items: center;
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

.metric-cards {
  display: flex;
  gap: var(--spacing-md);
  width: 100%;
  margin-top: var(--spacing-md);
}

.metric-card {
  flex: 1;
  background: var(--color-bg, #f5f7fa);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-sm);
  text-align: center;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
}

.metric-unit {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-left: 2px;
}

.metric-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.chart-box {
  width: 100%;
  height: 240px;
}

.panel-note {
  font-size: 12px;
  color: var(--color-text-light);
  text-align: center;
  margin-top: var(--spacing-sm);
}
</style>
