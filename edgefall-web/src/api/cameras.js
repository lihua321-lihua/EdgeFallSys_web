/**
 * 摄像头接口 - 设备同步、取流、布防、测试告警
 */
import request from '@/utils/request'

/** 摄像头列表（type=CAMERA） */
export function getCameras() {
  return request.get('/cameras')
}

/** 从萤石开放平台同步设备 */
export function syncCameras() {
  return request.post('/cameras/sync')
}

/** 获取取流地址（ezopen，前端 EZUIKit 播放） */
export function getStream(deviceSn, protocol = 1) {
  return request.get(`/cameras/${deviceSn}/stream`, { params: { protocol } })
}

/** 布防/撤防 */
export function toggleDefence(deviceSn, on = true) {
  return request.post(`/cameras/${deviceSn}/defence`, null, { params: { on } })
}

/** 手动触发测试告警（无需萤石平台配置） */
export function testEzvizAlert() {
  return request.post('/ezviz/callback/test')
}
