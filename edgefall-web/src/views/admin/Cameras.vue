<template>
  <div class="page-cameras">
    <h2 class="page-title">摄像头监控</h2>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="handleSync" :loading="syncing">同步萤石设备</el-button>
      <el-button type="warning" @click="handleTestAlert">测试告警</el-button>
      <el-tag v-if="!ezvizConfigured" type="info" size="small">萤石未配置</el-tag>
    </div>

    <el-row :gutter="16">
      <!-- 摄像头列表 -->
      <el-col :xs="24" :sm="8">
        <div class="camera-list">
          <div
            v-for="cam in cameras"
            :key="cam.device_sn"
            :class="['camera-item', { active: currentSn === cam.device_sn }]"
            @click="selectCamera(cam)"
          >
            <div class="cam-info">
              <div class="cam-sn">{{ cam.device_sn }}</div>
              <div v-if="cam.bind_elder" class="cam-elder">绑定：{{ cam.bind_elder }}</div>
            </div>
            <el-tag :type="cam.is_online ? 'success' : 'danger'" size="small">
              {{ cam.is_online ? '在线' : '离线' }}
            </el-tag>
          </div>
          <div v-if="!cameras.length" class="empty">
            暂无摄像头<br/>
            <span style="font-size:12px;color:var(--color-text-light)">请在设备管理添加序列号或点上方同步</span>
          </div>
        </div>
      </el-col>

      <!-- 视频播放 -->
      <el-col :xs="24" :sm="16">
        <div class="video-panel">
          <div v-if="currentSn" class="video-header">
            <span class="cam-title">📷 {{ currentSn }}</span>
            <div class="video-actions">
              <el-button size="small" type="success" @click="handleDefence(true)" :disabled="!ezvizConfigured">布防</el-button>
              <el-button size="small" @click="handleDefence(false)" :disabled="!ezvizConfigured">撤防</el-button>
            </div>
          </div>
          <div id="video-container" class="video-container"></div>
          <div v-if="!currentSn" class="video-empty">
            <span style="font-size:40px">📹</span>
            <p>请从左侧选择摄像头</p>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * 摄像头监控页 - 设备列表 + EZUIKit 实时播放 + 布防控制
 *
 * 取流流程：选摄像头 → getStream(device_sn) → ezopen URL + accessToken → EZUIKit 播放
 */
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getCameras, syncCameras, getStream, toggleDefence, testEzvizAlert } from '@/api/cameras'

const cameras = ref([])
const currentSn = ref('')
const ezvizConfigured = ref(false)
const syncing = ref(false)
let player = null

onMounted(() => loadCameras())
onBeforeUnmount(() => {
  try { player?.stop?.() } catch {}
  player = null
})

async function loadCameras() {
  try {
    const res = await getCameras()
    cameras.value = res.items || []
    ezvizConfigured.value = res.ezviz_configured
  } catch (e) {
    console.error('加载摄像头列表失败', e)
  }
}

async function selectCamera(cam) {
  if (currentSn.value === cam.device_sn) return
  currentSn.value = cam.device_sn
  await nextTick()
  await playVideo()
}

async function playVideo() {
  // 先停止旧播放器
  try { player?.stop?.() } catch {}
  player = null

  try {
    const res = await getStream(currentSn.value)
    // 动态加载 EZUIKit（避免构建时打包问题）
    const EZUIKit = await import('ezuikit-js')
    player = new EZUIKit.default.EZUIKitPlayer({
      id: 'video-container',
      url: res.url,
      accessToken: res.access_token,
      template: 'simple',
      width: '100%',
      height: '100%',
    })
  } catch (e) {
    ElMessage.error('取流失败：' + (e.message || '请确认萤石凭证已配置'))
  }
}

async function handleSync() {
  syncing.value = true
  try {
    const res = await syncCameras()
    ElMessage.success(res.message)
    await loadCameras()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    syncing.value = false
  }
}

async function handleDefence(on) {
  try {
    await toggleDefence(currentSn.value, on)
    ElMessage.success(on ? '布防成功' : '撤防成功')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function handleTestAlert() {
  try {
    await testEzvizAlert()
    ElMessage.success('测试告警已触发，查看告警列表')
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<style scoped>
.page-cameras {
  padding: 0;
}

.page-title {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-lg);
}

.toolbar {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.camera-list {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-sm);
  max-height: 500px;
  overflow-y: auto;
}

.camera-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.2s;
}

.camera-item:hover {
  background: var(--color-bg, #f5f7fa);
}

.camera-item.active {
  background: var(--color-primary);
  color: #fff;
}

.cam-sn {
  font-weight: 600;
  font-size: var(--font-size-base);
}

.cam-elder {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 2px;
}

.empty {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

.video-panel {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.cam-title {
  font-weight: 600;
  font-size: var(--font-size-base);
}

.video-container {
  flex: 1;
  width: 100%;
  min-height: 360px;
  background: #000;
}

.video-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-light);
  min-height: 360px;
}
</style>
