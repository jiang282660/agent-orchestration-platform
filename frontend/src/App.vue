<template>
  <el-container class="app">
    <el-aside width="220px" class="aside">
      <div class="logo">Agent 编排调度平台</div>
      <el-menu :default-active="active" @select="(k) => (active = k)">
        <el-menu-item index="overview"><el-icon><DataBoard /></el-icon>总览</el-menu-item>
        <el-menu-item index="kb"><el-icon><Folder /></el-icon>知识库</el-menu-item>
        <el-menu-item index="run"><el-icon><VideoPlay /></el-icon>任务运行</el-menu-item>
        <el-menu-item index="benchmark"><el-icon><DataAnalysis /></el-icon>基准评估</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="main">
      <component :is="views[active]" />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import Overview from './views/Overview.vue'
import KnowledgeBase from './views/KnowledgeBase.vue'
import RunBoard from './views/RunBoard.vue'
import Benchmark from './views/Benchmark.vue'

const active = ref('overview')
const views = { overview: Overview, kb: KnowledgeBase, run: RunBoard, benchmark: Benchmark }
</script>

<style>
body { margin: 0; }
.app { height: 100vh; }
.aside { background: #1f2d3d; }
.aside .logo { color: #fff; font-weight: 600; padding: 20px 16px; font-size: 15px; }
.aside .el-menu { border-right: none; background: transparent; }
.main { background: #f5f7fa; padding: 20px; }
</style>
