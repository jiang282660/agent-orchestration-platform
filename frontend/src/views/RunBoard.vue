<template>
  <div>
    <el-card>
      <el-form :inline="true">
        <el-form-item label="研究主题">
          <el-input v-model="topic" placeholder="例如：多智能体系统的工作流编排技术" style="width: 380px" />
        </el-form-item>
        <el-form-item label="知识库">
          <el-select v-model="kbId" placeholder="选择知识库" style="width: 220px">
            <el-option v-for="kb in kbs" :key="kb.id" :label="kb.name" :value="kb.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="running" @click="run">开始运行</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="timeline.length" style="margin-top: 16px">
      <template #header>执行过程（实时）</template>
      <el-timeline>
        <el-timeline-item v-for="(t, i) in timeline" :key="i"
          :type="t.color" :hollow="t.hollow" :timestamp="t.time">
          <b>{{ t.title }}</b>
          <div v-if="t.detail" class="detail">{{ t.detail }}</div>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-card v-if="scoreCurve.length" style="margin-top: 16px">
      <template #header>Self-Loop 评分曲线</template>
      <div class="curve">
        <span v-for="(s, i) in scoreCurve" :key="i" class="curve-item">
          <span class="round">第{{ i + 1 }}轮</span>
          <el-tag :type="s >= 0.8 ? 'success' : 'warning'">{{ s }}</el-tag>
          <span v-if="i < scoreCurve.length - 1" class="arrow">→</span>
        </span>
      </div>
    </el-card>

    <el-card v-if="ruleResult" style="margin-top: 16px">
      <template #header>规则核查（确定性）</template>
      <div class="rule-line">
        <el-tag :type="ruleResult.score >= 1 ? 'success' : 'warning'">
          通过 {{ ruleResult.passed }}/{{ ruleResult.total }} · 得分 {{ ruleResult.score }}
        </el-tag>
      </div>
      <div class="rule-checks">
        <el-tag v-for="(v, k) in ruleResult.checks" :key="k" size="small"
          :type="v ? 'success' : 'info'" style="margin: 2px 4px 0 0">{{ k }}：{{ v ? '✓' : '✗' }}</el-tag>
      </div>
    </el-card>

    <el-card v-if="report" style="margin-top: 16px">
      <template #header>最终报告</template>
      <div class="report" v-html="reportHtml"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { api } from '../api'

const kbs = ref([])
const topic = ref('多智能体系统的工作流编排技术')
const kbId = ref('')
const running = ref(false)
const events = ref([])
const scoreCurve = ref([])
const report = ref('')
const ruleResult = ref(null)

const reportHtml = computed(() => marked.parse(report.value || ''))

const NODE_LABEL = {
  planner: '规划者', analyze: '动态扇出', quality_loop: 'Self-Loop 循环',
  writer: '撰写者', reviewer: '审校者', retriever: '检索者', analyzer: '分析者', verifier: '验证者',
}

const timeline = computed(() => {
  return events.value.map((ev) => {
    if (ev.type === 'start') {
      return { title: `开始执行 ${NODE_LABEL[ev.node] || ev.node}`, color: 'primary', hollow: true, detail: '', time: '' }
    }
    if (ev.type === 'agent') {
      const tools = ev.tool_trace?.length ? `，调用工具 ${ev.tool_trace.length} 次` : ''
      const tokens = ev.tokens?.total_tokens != null ? ` · ${ev.tokens.total_tokens} tokens` : ''
      const lat = ev.latency_ms != null ? ` · ${ev.latency_ms}ms` : ''
      return { title: `${NODE_LABEL[ev.node] || ev.node} 完成${tools}`, color: 'primary', detail: truncate(ev.output), time: `${ev.steps} 步${tokens}${lat}` }
    }
    if (ev.type === 'rule') {
      return { title: '规则核查完成（确定性）', color: 'success', detail: `通过 ${ev.result.passed}/${ev.result.total}，得分 ${ev.result.score}`, time: '' }
    }
    if (ev.type === 'expand') {
      return { title: `动态扇出完成`, color: 'primary', detail: `${ev.items} 个子任务并行检索+分析`, time: '' }
    }
    if (ev.type === 'loop_iteration') {
      return { title: `Self-Loop 第 ${ev.iteration} 轮评分`, color: ev.score >= 0.8 ? 'success' : 'warning', detail: `评分 ${ev.score}`, time: '' }
    }
    if (ev.type === 'loop') {
      return { title: 'Self-Loop 结束', color: 'success', detail: `共 ${ev.iterations} 轮，评分曲线 ${ev.score_curve?.join(' → ')}`, time: '' }
    }
    if (ev.type === 'done') {
      return { title: '全部完成', color: 'success', detail: '已产出终稿与验证结果', time: '' }
    }
    if (ev.type === 'error') {
      return { title: '执行出错', color: 'danger', detail: ev.message, time: '' }
    }
    return { title: ev.type, color: 'info', detail: '', time: '' }
  })
})

function truncate(v) {
  if (v == null) return ''
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 80 ? s.slice(0, 80) + '…' : s
}

async function run() {
  if (!kbId.value) { ElMessage.warning('请先选择知识库'); return }
  running.value = true
  events.value = []
  scoreCurve.value = []
  report.value = ''
  try {
    const { run_id } = await api.createRun('research_report', { topic: topic.value, kb_id: kbId.value })
    const es = new EventSource(`/api/runs/${run_id}/events`)
    es.onmessage = (e) => {
      const ev = JSON.parse(e.data)
      events.value.push(ev)
      if (ev.type === 'loop_iteration') scoreCurve.value.push(ev.score)
      if (ev.type === 'done') {
        report.value = ev.final_state?.draft || ''
        ruleResult.value = ev.final_state?.rule_check || null
        es.close()
        running.value = false
      }
      if (ev.type === 'error') {
        es.close()
        running.value = false
        ElMessage.error(ev.message)
      }
    }
    es.onerror = () => { es.close(); running.value = false }
  } catch (e) {
    running.value = false
    ElMessage.error(e.message)
  }
}

onMounted(async () => {
  try { kbs.value = (await api.listKbs()).knowledge_bases; if (kbs.value.length) kbId.value = kbs.value[0].id } catch (e) { console.error(e) }
})
</script>

<style scoped>
.detail { color: #909399; font-size: 12px; margin-top: 4px; white-space: pre-wrap; }
.curve { display: flex; align-items: center; flex-wrap: wrap; }
.curve-item { display: flex; align-items: center; margin-right: 6px; }
.round { font-size: 12px; color: #909399; margin-right: 6px; }
.arrow { margin: 0 8px; color: #909399; }
.report { line-height: 1.7; }
.rule-line { margin-bottom: 8px; }
.rule-checks { display: flex; flex-wrap: wrap; }
.report :deep(h1) { font-size: 20px; }
.report :deep(h2) { font-size: 17px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
.report :deep(h3) { font-size: 15px; }
.report :deep(table) { border-collapse: collapse; }
.report :deep(td), .report :deep(th) { border: 1px solid #ddd; padding: 6px 10px; }
</style>
