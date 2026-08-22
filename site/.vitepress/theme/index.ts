import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import { useRoute } from 'vitepress'
import { onMounted, watch, nextTick } from 'vue'
import mediumZoom from 'medium-zoom'
import './zoom.css'

export default {
  extends: DefaultTheme,
  setup() {
    const route = useRoute()

    // Content images and the hero mark are click-to-zoom. Re-run after every
    // navigation: VitePress swaps page content without remounting the theme.
    const initZoom = () => {
      mediumZoom('.vp-doc img, .VPHero .image-src', {
        background: 'var(--vp-c-bg)',
        margin: 24
      })
    }

    onMounted(initZoom)
    watch(() => route.path, () => nextTick(initZoom))
  }
} satisfies Theme
