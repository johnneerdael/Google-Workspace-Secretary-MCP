<template>
  <div class="version-select">
    <select v-model="selectedVersion" @change="switchVersion" class="version-dropdown">
      <option v-for="ver in versions" :key="ver.version" :value="ver.path">
        {{ ver.label }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vitepress'

interface Version {
  version: string
  label: string
  path: string
}

interface VersionsData {
  latest: Version
  versions: Version[]
}

const router = useRouter()
const route = useRoute()
const selectedVersion = ref('')
const versions = ref<Version[]>([])

onMounted(async () => {
  try {
    // Fetch versions.json from the root of the site
    const base = '/Google-Workspace-Secretary-MCP/'
    const response = await fetch(`${base}versions.json`)
    const data: VersionsData = await response.json()
    
    // Combine latest + all versions
    versions.value = [data.latest, ...data.versions]
    
    // Determine current version from path
    const currentPath = route.path
    const match = currentPath.match(/^\/(latest|v[\d.]+)\//)
    if (match) {
      const versionPrefix = match[1]
      const found = versions.value.find(v => v.path.includes(versionPrefix))
      selectedVersion.value = found?.path || data.latest.path
    } else {
      selectedVersion.value = data.latest.path
    }
  } catch (error) {
    console.error('Failed to load versions:', error)
    // Fallback to latest
    versions.value = [{ version: 'latest', label: 'Latest (main)', path: '/latest/' }]
    selectedVersion.value = '/latest/'
  }
})

function switchVersion() {
  if (!selectedVersion.value) return
  
  const currentPath = route.path
  
  // Extract the page path after the version prefix
  const match = currentPath.match(/^\/(latest|v[\d.]+)\/(.*)/)
  const pagePath = match ? match[2] : ''
  
  // Construct new URL with selected version
  const base = '/Google-Workspace-Secretary-MCP'
  const newPath = `${base}${selectedVersion.value}${pagePath}`
  
  // Navigate to the new version, fallback to version root if page doesn't exist
  window.location.href = newPath
}
</script>

<style scoped>
.version-select {
  display: inline-block;
  margin-left: 12px;
}

.version-dropdown {
  background: var(--vp-c-bg-soft);
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 14px;
  color: var(--vp-c-text-1);
  cursor: pointer;
  transition: all 0.2s;
}

.version-dropdown:hover {
  border-color: var(--vp-c-brand-1);
}

.version-dropdown:focus {
  outline: none;
  border-color: var(--vp-c-brand-1);
  box-shadow: 0 0 0 2px var(--vp-c-brand-1-soft);
}

@media (max-width: 768px) {
  .version-select {
    margin-left: 0;
    margin-top: 8px;
  }
}
</style>
