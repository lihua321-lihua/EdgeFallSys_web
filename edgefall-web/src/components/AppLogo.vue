<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 120 120"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    class="edgefall-logo"
  >
    <!-- 盾牌外形 -->
    <path
      d="M60 10 L105 30 L105 65 C105 88 85 105 60 115 C35 105 15 88 15 65 L15 30 Z"
      :fill="bgFill"
      opacity="0.12"
    />
    <path
      d="M60 10 L105 30 L105 65 C105 88 85 105 60 115 C35 105 15 88 15 65 L15 30 Z"
      :stroke="primaryColor"
      stroke-width="4"
      fill="none"
    />
    <!-- E 字母 -->
    <text
      x="60"
      y="72"
      text-anchor="middle"
      :fill="primaryColor"
      font-size="48"
      font-weight="700"
      font-family="Arial, sans-serif"
    >E</text>
    <!-- 信号波纹（右上角） -->
    <path
      d="M88 22 Q98 16 98 28"
      :stroke="primaryColor"
      stroke-width="2.5"
      fill="none"
      stroke-linecap="round"
    />
    <path
      d="M92 16 Q106 8 106 26"
      :stroke="primaryColor"
      stroke-width="2"
      fill="none"
      stroke-linecap="round"
      opacity="0.6"
    />
    <!-- 心形（左下角，代表守护） -->
    <path
      d="M28 82 C28 76 36 72 40 78 C44 72 52 76 52 82 C52 90 40 96 40 96 C40 96 28 90 28 82Z"
      :fill="primaryColor"
      opacity="0.5"
    />
  </svg>
</template>

<script setup>
/**
 * EdgeFall Logo 组件 - 盾牌+信号波纹+心形守护图标
 */
defineProps({
  size: { type: [Number, String], default: 40 },
  primaryColor: { type: String, default: '#409EFF' },
  bgFill: { type: String, default: '#409EFF' },
})
</script>

<style scoped>
.edgefall-logo {
  display: inline-block;
  flex-shrink: 0;
}
</style>
