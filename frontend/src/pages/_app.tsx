import '../styles/globals.css'
import type { AppProps } from 'next/app'
import { useRouter } from 'next/router'
import { useEffect } from 'react'
import { AuthProvider } from '@/contexts/AuthContext'
import Layout from '@/components/layout/layout'

// List of routes that don't require authentication
const publicRoutes = [
  '/',
  '/login',
  '/register',
  '/signup',
  '/forgot-password',
  '/reset-password',
  '/auth/success',
  '/auth/error',
  '/auth/callback',
  '/privacy',
  '/terms',
  '/support',
  '/about'
]

// List of routes that should redirect authenticated users away from
const authRoutes = [
  '/login',
  '/register',
  '/signup'
]

// Pages that shouldn't have the dashboard layout
const pagesWithoutLayout = [
  '/', 
  '/login', 
  '/register', 
  '/signup',
  '/forgot-password',
  '/reset-password',
  '/auth/success',
  '/auth/error',
  '/privacy',
  '/terms',
  '/support',
  '/about'
]

function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter()

  // Handle route changes for analytics, etc.
  useEffect(() => {
    const handleRouteChange = (url: string) => {
      // Add analytics tracking here if needed
      console.log('Route changed to:', url)
    }

    const handleRouteChangeStart = () => {
      // Add loading state if needed
    }

    const handleRouteChangeComplete = () => {
      // Remove loading state if needed
    }

    router.events.on('routeChangeStart', handleRouteChangeStart)
    router.events.on('routeChangeComplete', handleRouteChange)
    router.events.on('routeChangeComplete', handleRouteChangeComplete)
    router.events.on('routeChangeError', handleRouteChangeComplete)
    
    return () => {
      router.events.off('routeChangeStart', handleRouteChangeStart)
      router.events.off('routeChangeComplete', handleRouteChange)
      router.events.off('routeChangeComplete', handleRouteChangeComplete)
      router.events.off('routeChangeError', handleRouteChangeComplete)
    }
  }, [router.events])

  // Check if current route is public
  const isPublicRoute = publicRoutes.some(route => {
    if (route === '/') return router.pathname === '/'
    return router.pathname.startsWith(route)
  })

  // Check if current route is auth route  
  const isAuthRoute = authRoutes.some(route => {
    return router.pathname === route
  })

  // Check if should show layout
  const shouldShowLayout = !pagesWithoutLayout.some(route => {
    if (route === '/') return router.pathname === '/'
    return router.pathname.startsWith(route)
  })

  // Check if it's an OAuth callback route
  const isOAuthCallback = router.pathname.startsWith('/auth/callback/')

  return (
    <AuthProvider>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {shouldShowLayout ? (
          <Layout>
            <Component {...pageProps} />
          </Layout>
        ) : (
          <Component {...pageProps} />
        )}
      </div>
    </AuthProvider>
  )
}

export default MyApp