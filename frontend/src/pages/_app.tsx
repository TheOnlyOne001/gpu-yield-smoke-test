import '../styles/globals.css'
import type { AppProps } from 'next/app'
import Layout from '@/components/layout/layout'
import { useRouter } from 'next/router'

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter()
  
  // Pages that shouldn't have the dashboard layout
  const pagesWithoutLayout = ['/', '/login', '/register']
  const shouldShowLayout = !pagesWithoutLayout.includes(router.pathname)
  
  if (shouldShowLayout) {
    return (
      <Layout>
        <Component {...pageProps} />
      </Layout>
    )
  }
  
  // For landing page and auth pages without layout
  return <Component {...pageProps} />
}