<template>
  <div>
    <el-card>
      <template #header>
        <div class="card-head">
          <span>知识库列表</span>
          <el-button type="primary" size="small" @click="createDialog = true">新建知识库</el-button>
        </div>
      </template>
      <el-table :data="kbs" size="small" @row-click="(row) => selectKb(row)">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="id" label="ID" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="检索">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.retriever_type || 'bm25' }}</el-tag>
            <el-tag v-if="row.semantic_retrieval" size="small" type="success" style="margin-left: 4px">语义</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-upload :show-file-list="false" :before-upload="(f) => upload(row.id, f)">
              <el-button size="small">上传文档</el-button>
            </el-upload>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="selected" style="margin-top: 16px">
      <template #header>{{ selected.name }} · 文档与检索</template>
      <el-table :data="docs" size="small" style="margin-bottom: 12px">
        <el-table-column prop="filename" label="文档" />
        <el-table-column prop="chunks_count" label="分块数" />
        <el-table-column prop="status" label="状态" />
      </el-table>
      <el-input v-model="query" placeholder="输入检索问题" style="width: 360px" />
      <el-button type="primary" @click="doSearch" style="margin-left: 8px">检索</el-button>
      <div v-for="(r, i) in results" :key="i" class="search-item">
        <div class="score">score {{ r.score }} · 来源 {{ r.metadata.source }}</div>
        <div class="text">{{ r.text }}</div>
      </div>
    </el-card>

    <el-dialog v-model="createDialog" title="新建知识库" width="420px">
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="newKb.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="newKb.description" /></el-form-item>
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
const selected = ref(null)
const docs = ref([])
const results = ref([])
const query = ref('')
const createDialog = ref(false)
const newKb = ref({ name: '', description: '' })

async function load() { kbs.value = (await api.listKbs()).knowledge_bases }

async function selectKb(row) {
  selected.value = row
  docs.value = (await api.listDocs(row.id)).documents
  results.value = []
}

async function upload(kbId, file) {
  try {
    await api.uploadDoc(kbId, file)
    ElMessage.success('上传成功')
    if (selected.value?.id === kbId) docs.value = (await api.listDocs(kbId)).documents
  } catch (e) { ElMessage.error(e.message) }
  return false
}

async function doSearch() {
  try {
    results.value = (await api.search(selected.value.id, query.value)).results
  } catch (e) { ElMessage.error(e.message) }
}

async function doCreate() {
  try {
    await api.createKb(newKb.value)
    createDialog.value = false
    newKb.value = { name: '', description: '' }
    await load()
    ElMessage.success('创建成功')
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(load)
</script>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.search-item { border: 1px solid #eee; border-radius: 6px; padding: 10px; margin-top: 10px; }
.search-item .score { color: #909399; font-size: 12px; }
.search-item .text { margin-top: 6px; white-space: pre-wrap; }
</style>
