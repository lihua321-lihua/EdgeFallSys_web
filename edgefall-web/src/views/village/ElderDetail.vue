<template>
  <div class="page-elder-detail">
    <!-- 面包屑 -->
    <div class="breadcrumb">
      <router-link :to="rosterRoute">老人名册</router-link>
      <span class="separator">&gt;</span>
      <span class="current">{{ elder.name || '加载中...' }}</span>
    </div>

    <div v-if="loading" class="skeleton-wrap">
      <div class="skeleton" style="height:200px;margin-bottom:16px"></div>
      <div class="skeleton" style="height:150px"></div>
    </div>

    <div v-else class="detail-layout">
      <!-- 左侧：基础信息卡片 -->
      <div class="detail-card">
        <div class="card-head">👤 基础信息</div>
        <div class="card-body">
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">姓名</span>
              <span class="info-value">{{ elder.name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">年龄</span>
              <span class="info-value">{{ elder.age }} 岁</span>
            </div>
            <div class="info-item">
              <span class="info-label">性别</span>
              <span class="info-value">{{ elder.gender }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">住址</span>
              <span class="info-value">{{ elder.address }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">手环编号</span>
              <span class="info-value">{{ elder.device_sn }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">网关编号</span>
              <span class="info-value">{{ elder.gateway_sn }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">家属电话</span>
              <span class="info-value">{{ elder.emergency_contact }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">紧急联系人</span>
              <span class="info-value">{{ elder.emergency_relation }}</span>
            </div>
            <div class="info-item full-width">
              <span class="info-label">既往病史</span>
              <span class="info-value">{{ elder.medical_history }}</span>
            </div>
            <div class="info-item full-width">
              <span class="info-label">绑定时长</span>
              <span class="info-value">{{ elder.bind_duration }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：健康评估面板 -->
      <div>
        <!-- AI 月度评估 -->
        <div class="health-report">
          <div class="report-title">
            🧠 AI 月度健康评估
            <el-button
              type="primary"
              size="small"
              plain
              :loading="monthlyRegenerating"
              @click="regenerateMonthly"
              style="margin-left: 8px"
            >
              重新生成
            </el-button>
          </div>
          <div v-if="reportLoading" class="skeleton" style="height:80px;margin:12px 0"></div>
          <template v-else-if="aiReport">
            <div class="report-tags">
              <el-tag
                v-for="tag in aiReport.risk_tags"
                :key="tag"
                :type="tag.includes('跌倒') || tag.includes('情绪') ? 'danger' : 'warning'"
                size="small"
                style="margin-right: 4px"
              >
                {{ tag }}
              </el-tag>
            </div>
            <p class="report-text">{{ aiReport.ai_summary }}</p>
            <div class="report-meta">
              📅 评估时间：{{ aiReport.report_date }} &nbsp;|&nbsp; 数据来源：{{ aiReport.data_source }}
            </div>
          </template>
          <EmptyState v-else icon="📋" text="暂无AI评估报告" />
        </div>

        <!-- AI 长期健康分析报告（10 模块） -->
        <div class="health-report" style="margin-top: var(--spacing-lg);">
          <div class="report-title">
            📊 AI 长期健康分析报告
            <el-button
              type="primary"
              size="small"
              plain
              :loading="healthAnalysisLoading"
              @click="generateHealthAnalysis"
              style="margin-left: 8px"
            >
              {{ healthAnalysisReport ? '重新生成' : '生成报告' }}
            </el-button>
          </div>
          <div v-if="healthAnalysisLoading" class="skeleton" style="height:80px;margin:12px 0"></div>
          <template v-else-if="healthAnalysisReport">
            <div class="report-tags">
              <el-tag
                :type="healthAnalysisReport.source === 'qwen' ? 'success' : 'info'"
                size="small"
              >
                {{ healthAnalysisReport.source === 'qwen' ? 'AI 大模型生成' : '本地模板兜底' }}
              </el-tag>
              <span class="report-meta" style="margin-left: 8px">
                📅 {{ healthAnalysisReport.created_at }}
              </span>
              <el-button-group style="margin-left: 8px">
                <el-button size="small" @click="downloadHealthAnalysis('json')">JSON</el-button>
                <el-button size="small" @click="downloadHealthAnalysis('txt')">TXT</el-button>
              </el-button-group>
            </div>
            <el-collapse v-model="healthActiveKeys" class="health-collapse">
              <el-collapse-item
                v-for="(item, idx) in healthModules"
                :key="item.key"
                :name="item.key"
                :title="`${idx + 1}. ${item.title}`"
              >
                <p class="report-text" style="margin: 0">{{ healthAnalysisReport.report[item.key] || '（无）' }}</p>
              </el-collapse-item>
            </el-collapse>
          </template>
          <EmptyState v-else icon="📊" text="点击「生成报告」进行长期健康数据分析" />
        </div>

        <!-- 近期活动记录 -->
        <div class="detail-card" style="margin-top: var(--spacing-lg);">
          <div class="card-head">🕐 近期门磁活动记录</div>
          <div class="card-body">
            <el-timeline>
              <el-timeline-item
                v-for="act in elder.recent_activities"
                :key="act.date"
                :type="activityType(act.status)"
                :timestamp="act.date"
                placement="top"
              >
                <span v-if="act.open">
                  {{ act.open }} 开门外出 → {{ act.close }} 返回家中
                </span>
                <span v-else>未检测到开门</span>
                <el-tag
                  :type="activityTagType(act.status)"
                  size="small"
                  style="margin-left: 8px"
                >
                  {{ activityLabel(act.status) }}
                </el-tag>
              </el-timeline-item>
            </el-timeline>
          </div>
        </div>

        <!-- 返回按钮 -->
        <div style="margin-top: var(--spacing-lg);">
          <el-button @click="$router.push(rosterRoute)">&larr; 返回老人名册</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 老人详情 - 基础信息、AI健康评估、门磁活动时间线
 * P0 修正：面包屑和返回按钮按角色使用 /grid 或 /doctor 前缀
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getElderDetail, getElderAiReport } from '@/api/elders'
import { generateHealthAnalysis as generateHealthAnalysisApi, getAiReports, getAiReport, downloadAiReport, regenerateMonthlyReport } from '@/api/ai'
import { useAuthStore } from '@/store/useAuthStore'
import { ElMessage } from 'element-plus'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const authStore = useAuthStore()

const elder = ref({})
const aiReport = ref(null)
const loading = ref(true)
const reportLoading = ref(true)
const monthlyRegenerating = ref(false)

// AI 长期健康分析报告（10 模块）
const healthAnalysisReport = ref(null)
const healthAnalysisLoading = ref(false)
const healthActiveKeys = ref([])
const healthModules = [
  { key: 'overall_assessment', title: '健康综合评估' },
  { key: 'cardiovascular_risk', title: '心血管风险分析' },
  { key: 'fall_root_cause', title: '跌倒深层诱因分析' },
  { key: 'medication_compliance', title: '用药合规提醒' },
  { key: 'activity_sleep', title: '活动/睡眠评估' },
  { key: 'high_risk_list', title: '高危预警清单' },
  { key: 'tiered_intervention', title: '分级干预措施' },
  { key: 'village_doctor_followup', title: '村医随访计划' },
  { key: 'family_care_advice', title: '子女日常关怀建议' },
  { key: 'trend_forecast_review', title: '长期趋势预测与复查建议' },
]

// P0: 按角色返回对应端的名册路由
const rosterRoute = computed(() => {
  return authStore.role === 'village_doctor' ? '/doctor/elder-roster' : '/grid/elder-roster'
})

function activityType(status) {
  return { normal: 'success', warning: 'warning', danger: 'danger' }[status] || 'info'
}

function activityTagType(status) {
  return { normal: 'success', warning: 'warning', danger: 'danger' }[status] || 'info'
}

function activityLabel(status) {
  return { normal: '正常', warning: '异常', danger: '连续3天' }[status] || ''
}

async function loadDetail() {
  loading.value = true
  reportLoading.value = true
  const id = route.params.id
  try {
    const [detailRes, reportRes] = await Promise.allSettled([
      getElderDetail(id),
      getElderAiReport(id),
    ])
    if (detailRes.status === 'fulfilled') {
      elder.value = detailRes.value
    }
    if (reportRes.status === 'fulfilled') {
      aiReport.value = reportRes.value
    }
    // 加载最近一份长期健康分析报告（已生成则展示，未生成则空态）
    try {
      const list = await getAiReports({ elder_id: id, report_type: 'health_analysis', limit: 1 })
      if (list?.items?.length) {
        const detail = await getAiReport(list.items[0].report_id)
        healthAnalysisReport.value = detail
        healthActiveKeys.value = ['overall_assessment', 'high_risk_list']
      }
    } catch (e) {
      // 查询失败忽略，保持空态
    }
  } catch (e) {
    console.error('加载老人详情失败', e)
  } finally {
    loading.value = false
    reportLoading.value = false
  }
}

// 重新生成本月 AI 月度健康评估（大模型，基于本月监测数据，覆盖固定字样）
async function regenerateMonthly() {
  const id = route.params.id
  monthlyRegenerating.value = true
  try {
    const data = await regenerateMonthlyReport(id)
    aiReport.value = {
      ...aiReport.value,
      ai_summary: data.ai_summary,
      report_date: data.report_month,
      data_source: '大模型生成',
    }
    ElMessage.success('月度健康评估已由大模型重新生成')
  } catch (e) {
    ElMessage.error('月度评估生成失败')
  } finally {
    monthlyRegenerating.value = false
  }
}

// 生成 AI 长期健康分析报告（10 模块）
async function generateHealthAnalysis() {
  const id = route.params.id
  healthAnalysisLoading.value = true
  try {
    const data = await generateHealthAnalysisApi({ elder_id: id, days: 30 })
    healthAnalysisReport.value = data
    healthActiveKeys.value = ['overall_assessment', 'high_risk_list']
    ElMessage.success('健康分析报告已生成')
  } catch (e) {
    ElMessage.error('健康分析报告生成失败')
  } finally {
    healthAnalysisLoading.value = false
  }
}

// 下载长期健康分析报告
async function downloadHealthAnalysis(format) {
  if (!healthAnalysisReport.value?.report_id) return
  try {
    await downloadAiReport(healthAnalysisReport.value.report_id, format)
    ElMessage.success(`已下载 ${format.toUpperCase()} 文件`)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

onMounted(() => {
  loadDetail()
})
</script>

<style scoped>
.page-elder-detail {
  padding: 0;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.breadcrumb a {
  color: var(--color-primary);
  text-decoration: none;
}

.breadcrumb a:hover {
  text-decoration: underline;
}

.breadcrumb .separator {
  color: var(--color-text-light);
}

.breadcrumb .current {
  color: var(--color-text);
  font-weight: 500;
}

.skeleton-wrap {
  padding: var(--spacing-md);
}

.detail-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: var(--spacing-lg);
}

.detail-card {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.detail-card .card-head {
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border-light);
  background: #FAFAFA;
}

.detail-card .card-body {
  padding: var(--spacing-md);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-sm) var(--spacing-md);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.info-value {
  font-size: var(--font-size-base);
  color: var(--color-text);
  font-weight: 500;
}

/* AI 报告 */
.health-report {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-md);
}

.health-report .report-title {
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-sm);
  display: flex;
  align-items: center;
}

.health-report .report-tags {
  margin-bottom: var(--spacing-sm);
}

.health-report .report-text {
  font-size: var(--font-size-base);
  color: var(--color-text);
  line-height: 1.8;
  margin: var(--spacing-sm) 0;
}

.health-report .report-meta {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.health-collapse {
  max-height: 480px;
  overflow-y: auto;
  margin-top: var(--spacing-sm);
}

/* 响应式 */
@media (max-width: 768px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }
}
</style>
