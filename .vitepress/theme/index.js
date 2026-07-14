import DefaultTheme from 'vitepress/theme'
import './custom.css'
import HomeMap from './components/HomeMap.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('HomeMap', HomeMap)
  }
}
