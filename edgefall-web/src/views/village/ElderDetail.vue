<template>
  <div class="page-elder-detail">
    <!-- 面包屑 -->
    <div class="breadcrumb">
      <router-link to="/village/elder-roster">老人名册</router-link>
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
          <div class="report-title">🧠 AI 月度健康评估</div>
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
          <el-button @click="$router.push('/village/elder-roster')">&larr; 返回老人名册</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 老人详情 - 基础信息、AI健康评估、门磁活动时间线
 */
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getElderDetail, getElderAiReport } from '@/api/elders'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()

const elder = ref({})
const aiReport = ref(null)
const loading = ref(true)
const reportLoading = ref(true)

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
  } catch (e) {
    console.error('加载老人详情失败', e)
  } finally {
    loading.value = false
    reportLoading.value = false
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

/* 响应式 */
@media (max-width: 768px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }
}
</style>
