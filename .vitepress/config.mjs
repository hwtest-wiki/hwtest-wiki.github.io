import { defineConfig } from 'vitepress'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const sidebar = JSON.parse(
  readFileSync(fileURLToPath(new URL('./sidebar.json', import.meta.url)), 'utf-8')
)

// 部署到 GitHub Pages 项目站点时，base 需为 /<仓库名>/；本地开发为 /。
// GitHub Actions 通过 SITE_BASE 注入（actions/configure-pages 的 base_path）。
const rawBase = process.env.SITE_BASE || '/'
const base = rawBase.endsWith('/') ? rawBase : rawBase + '/'

export default defineConfig({
  base,
  lang: 'zh-CN',
  title: '硬件测试科普百科',
  description: '消费电子硬件测试知识库：通俗讲解 + 工程师速查，可全文搜索',
  lastUpdated: true,
  cleanUrls: true,
  ignoreDeadLinks: true,
  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '全部文章', link: '/articles/01' }
    ],
    sidebar: {
      '/': sidebar,
      '/articles/': sidebar
    },
    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索', buttonAriaLabel: '搜索' },
          modal: {
            noResultsText: '没有找到结果',
            resetButtonTitle: '清除',
            footer: { selectText: '选择', navigateText: '切换' }
          }
        }
      }
    },
    outline: { level: [2, 3], label: '本页目录' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    darkModeSwitchLabel: '主题',
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '目录',
    lastUpdatedText: '最后更新',
    footer: {
      message: '硬件测试科普系列 · 知识沉淀',
      copyright: '内容仅供学习参考'
    }
  }
})
