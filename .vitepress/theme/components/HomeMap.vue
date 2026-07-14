<script setup>
import { withBase } from 'vitepress'
import data from '../modules.json'

const blocks = [...data.modules, ...data.extra]
</script>

<template>
  <div class="km">
    <div class="km-head">
      <h2 class="km-h2">🗺 知识地图</h2>
      <p class="km-sub">
        已收录 <b>{{ data.stats.articles }}</b> 篇 ·
        <b>{{ data.stats.modules_active }}</b> 个模块在更 ·
        点开任意一块直达
        <span class="km-legend"><i>🔧</i> = 含工程师速查</span>
      </p>
    </div>

    <div class="km-grid">
      <section
        v-for="m in blocks"
        :key="m.key"
        class="km-mod"
        :class="{ 'is-planned': m.status === 'planned', 'is-extra': typeof m.key === 'string' }"
      >
        <header class="km-mod-h">
          <span class="km-ico">{{ m.icon }}</span>
          <span class="km-badge">{{ m.badge }}</span>
          <h3 class="km-title">{{ m.title }}</h3>
          <span v-if="m.status === 'planned'" class="km-soon">规划中</span>
          <span v-else class="km-cnt">{{ m.articles.length }} 篇</span>
        </header>

        <div v-if="m.status === 'active'" class="km-caps">
          <a
            v-for="a in m.articles"
            :key="a.nn"
            class="km-cap"
            :href="withBase('/articles/' + a.nn)"
          >
            <b class="km-nn">{{ a.nn }}</b>
            <span class="km-name">{{ a.name }}</span>
            <i v-if="a.qr" class="km-qr" title="含工程师速查">🔧</i>
          </a>
        </div>
        <p v-else class="km-note">{{ m.note }}</p>
      </section>
    </div>
  </div>
</template>
