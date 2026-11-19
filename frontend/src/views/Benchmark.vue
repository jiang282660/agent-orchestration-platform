<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-head">
          <span>基准集（golden set）</span>
          <el-button type="primary" size="small" @click="createDialog = true">新建基准集</el-button>
        </div>
      </template>
      <el-table :data="benchmarks" size="small">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-select v-model="runKbId" placeholder="选知识库" size="small" style="width: 180px">
              <el-option v-for="kb in kbs" :key="kb.id" :label="kb.name" :value="kb.id" />
            </el-select>
            <el-button size="small" type="primary" :loading="running" @click="doRun(row.id)">运行评估</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="results.length" style="margin-top: 16px">
      <template #header>评估结果（平均覆盖度 {{ avg }}）</template>
      <div v-for="(r, i) in results" :key="i" class="result">
        <div class="q">{{ i + 1 }}. {{ r.question }}</div>
        <el-progress :percentage="Math.round(r.coverage * 100)" :status="r.coverage >= 0.7 ? 'success' : 'warning'" />
        <div class="pts">覆盖：{{ r.covered.join('、') || '无' }}</div>
        <div class="pts miss">缺失：{{ r.missing.join('、') || '无' }}</div>
      </div>
    </el-card>

    <el-dialog v-model="createDialog" title="新建基准集" width="640px">
      <el-form label-width="90px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="评测项">
          <div v-for="(item, i) in form.items" :key="i" class="item-row">
            <el-input v-model="item.question" placeholder="问题" style="width: 45%" />
            <el-input v-model="item.points" placeholder="必覆盖要点（逗号分隔）" style="width: 45%" />
            <el-button size="small" @click="form.items.splice(i, 1)">删</el-button>
          </div>
          <el-button size="small" @click="form.items.push({ question: '', points: '' })">+ 添加评测项</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const kbs = ref([])
const benchmarks = ref([])
const results = ref([])
const avg = ref(0)
const running = ref(false)
const runKbId = ref('')
const createDialog = ref(false)
const form = ref({ name: '', description: '', items: [{ question: '', points: '' }] })

async function load() { benchmarks.value = (await api.listBenchmarks()).benchmarks }

async function doRun(bId) {
  if (!runKbId.value) { ElMessage.warning('请选择知识库'); return }
  running.value = true
  try {
    const res = await api.runBenchmark(bId, runKbId.value)
    results.value = res.results
    avg.value = res.avg_coverage
  } catch (e) { ElMessage.error(e.message) }
  running.value = false
}

async function doCreate() {
  try {
    const items = form.value.items
      .filter((i) => i.question && i.points)
      .map((i) => ({ question: i.question, golden_points: i.points.split(/[,，]/).map((s) => s.trim()).filter(Boolean) }))
    await api.createBenchmark({ name: form.value.name, description: form.value.description, items })
    createDialog.value = false
    form.value = { name: '', description: '', items: [{ question: '', points: '' }] }
    await load()
    ElMessage.success('创建成功')
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(async () => {
  try { kbs.value = (await api.listKbs()).knowledge_bases; if (kbs.value.length) runKbId.value = kbs.value[0].id } catch (e) { console.error(e) }
  load()
})
</script>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.item-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
.result { border: 1px solid #eee; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
.result .q { font-weight: 600; margin-bottom: 8px; }
.pts { font-size: 12px; color: #67c23a; margin-top: 4px; }
.pts.miss { color: #e6a23c; }
</style>
