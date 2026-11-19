async function request(path, options = {}) {
  const resp = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || resp.statusText)
  }
  return resp.json()
}

export const api = {
  // 知识库
  listKbs: () => request('/api/kb'),
  createKb: (data) => request('/api/kb', { method: 'POST', body: JSON.stringify(data) }),
  uploadDoc: (kbId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return fetch(`/api/kb/${kbId}/documents`, { method: 'POST', body: fd }).then((r) => r.json())
  },
  listDocs: (kbId) => request(`/api/kb/${kbId}/documents`),
  search: (kbId, query) => request(`/api/kb/${kbId}/search`, { method: 'POST', body: JSON.stringify({ query }) }),
  // 团队 / 工作流
  listAgents: () => request('/api/agents'),
  listWorkflows: () => request('/api/workflows'),
  getWorkflow: (name) => request(`/api/workflows/${name}`),
  // 运行
  createRun: (workflowName, input) =>
    request('/api/runs', { method: 'POST', body: JSON.stringify({ workflow_name: workflowName, input }) }),
  getRun: (runId) => request(`/api/runs/${runId}`),
  // 基准集
  listBenchmarks: () => request('/api/benchmarks'),
  createBenchmark: (data) => request('/api/benchmarks', { method: 'POST', body: JSON.stringify(data) }),
  runBenchmark: (bId, kbId) =>
    request(`/api/benchmarks/${bId}/run`, { method: 'POST', body: JSON.stringify({ kb_id: kbId }) }),
}
