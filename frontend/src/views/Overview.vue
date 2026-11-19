<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header>Agent 团队（六角色）</template>
          <el-table :data="agents" size="small">
            <el-table-column prop="name" label="角色" />
            <el-table-column prop="id" label="ID" />
            <el-table-column label="工具">
              <template #default="{ row }">{{ row.tools.length ? row.tools.join(', ') : '—' }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>预置工作流</template>
          <el-table :data="workflows" size="small">
            <el-table-column prop="name" label="名称" />
            <el-table-column label="节点">
              <template #default="{ row }">{{ row.nodes.join(' → ') }}</template>
            </el-table-column>
          </el-table>
          <el-alert style="margin-top: 12px" type="info" :closable="false"
            title="研究报告中 planner 规划 → analyze 动态扇出并行检索/分析 → quality_loop 撰写↔审校 Self-Loop → 规则核查 + verifier 事实核查" />
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 16px">
      <template #header>工作流 DAG（编排可视化）</template>
      <div class="dag-wrap">
        <svg :viewBox="`0 0 ${dag.width} ${dag.height}`" class="dag">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="#909399" />
            </marker>
          </defs>
          <g v-for="e in dag.edges" :key="e.from + e.to">
            <line :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2" stroke="#909399" stroke-width="1.5" marker-end="url(#arrow)" />
          </g>
          <g v-for="n in dag.nodes" :key="n.id">
            <rect :x="n.x" :y="n.y" :width="n.w" :height="n.h" rx="8" class="dag-node" :class="'dag-' + n.type" />
            <text :x="n.x + n.w / 2" :y="n.y + 26" text-anchor="middle" class="dag-name">{{ n.label }}</text>
            <text :x="n.x + n.w / 2" :y="n.y + 44" text-anchor="middle" class="dag-type">{{ n.typeLabel }}</text>
            <text v-if="n.sub" :x="n.x + n.w / 2" :y="n.y + 64" text-anchor="middle" class="dag-sub">{{ n.sub }}</text>
          </g>
        </svg>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

const agents = ref([])
const workflows = ref([])
const wf = ref(null)

const NODE_LABEL = {
  planner: '规划者', analyze: '动态扇出', quality_loop: 'Self-Loop 循环',
  rule_gate: '规则核查', verifier: '验证者',
  writer: '撰写者', reviewer: '审校者', retriever: '检索者', analyzer: '分析者',
}
const TYPE_LABEL = { agent: 'Agent', expand: '动态扇出', loop: 'Self-Loop', rule: '规则核查' }

function subLabel(n) {
  if (n.type === 'expand' && n.subgraph) return n.subgraph.map((s) => NODE_LABEL[s.id] || s.id).join(' → ')
  if (n.type === 'loop' && n.body) return n.body.map((s) => NODE_LABEL[s.id] || s.id).join(' → ')
  return ''
}

const dag = computed(() => {
  if (!wf.value) return { nodes: [], edges: [], width: 0, height: 0 }
  const nodes = wf.value.nodes
  const level = {}
  let changed = true
  while (changed) {
    changed = false
    for (const n of nodes) {
      const deps = n.depends_on || []
      const lv = deps.length ? 1 + Math.max(...deps.map((d) => level[d] ?? -1)) : 0
      if (lv < 0) continue
      if (level[n.id] !== lv) { level[n.id] = lv; changed = true }
    }
  }
  const byLevel = {}
  for (const n of nodes) { (byLevel[level[n.id]] ||= []).push(n) }

  const W = 160, H = 80, GX = 130, GY = 46, PAD = 30
  const maxInLevel = Math.max(...Object.values(byLevel).map((a) => a.length), 1)
  const maxLevel = Math.max(...Object.values(level), 0)
  const height = PAD * 2 + maxInLevel * H + (maxInLevel - 1) * GY
  const width = PAD * 2 + (maxLevel + 1) * W + maxLevel * GX

  const nodeMap = {}
  const pos = []
  for (const lvStr of Object.keys(byLevel)) {
    const lv = Number(lvStr)
    const arr = byLevel[lvStr]
    const x = PAD + lv * (W + GX)
    const totalH = arr.length * H + (arr.length - 1) * GY
    let y = (height - totalH) / 2
    for (const n of arr) {
      nodeMap[n.id] = { x, y }
      pos.push({ id: n.id, label: NODE_LABEL[n.id] || n.id, type: n.type,
        typeLabel: TYPE_LABEL[n.type] || n.type, sub: subLabel(n), x, y, w: W, h: H })
      y += H + GY
    }
  }

  const edges = []
  for (const n of nodes) {
    for (const d of n.depends_on || []) {
      if (nodeMap[d] && nodeMap[n.id]) {
        edges.push({ from: d, to: n.id,
          x1: nodeMap[d].x + W, y1: nodeMap[d].y + H / 2,
          x2: nodeMap[n.id].x, y2: nodeMap[n.id].y + H / 2 })
      }
    }
  }
  return { nodes: pos, edges, width, height }
})

onMounted(async () => {
  try {
    agents.value = (await api.listAgents()).agents
    workflows.value = (await api.listWorkflows()).workflows
    const name = workflows.value[0]?.name || 'research_report'
    wf.value = await api.getWorkflow(name)
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.dag-wrap { overflow-x: auto; }
.dag { min-width: 720px; max-height: 420px; }
.dag-node { stroke-width: 1.5; }
.dag-agent { fill: #ecf5ff; stroke: #409eff; }
.dag-expand { fill: #fdf6ec; stroke: #e6a23c; }
.dag-loop { fill: #f0e6ff; stroke: #a855f7; }
.dag-rule { fill: #f0f9eb; stroke: #67c23a; }
.dag-name { font-size: 14px; font-weight: 600; fill: #303133; }
.dag-type { font-size: 11px; fill: #909399; }
.dag-sub { font-size: 10px; fill: #606266; }
</style>
