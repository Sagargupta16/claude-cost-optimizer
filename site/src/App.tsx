import { useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import Home from './pages/Home'
import Calculator from './pages/Calculator'
import BadgeChecker from './pages/BadgeChecker'
import RepoAnalyzer from './pages/RepoAnalyzer'
import styles from './App.module.css'

function App() {
  const { pathname } = useLocation()

  // A route change keeps the old scroll position by default; start each page at the top.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <div className={styles.layout}>
      <a href="#main" className={styles.skip}>
        Skip to content
      </a>
      <Navbar />
      <main id="main" className={styles.main} tabIndex={-1}>
        <div key={pathname} className={styles.page}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/calculator" element={<Calculator />} />
            <Route path="/badge" element={<BadgeChecker />} />
            <Route path="/analyzer" element={<RepoAnalyzer />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </div>
      </main>
      <Footer />
    </div>
  )
}

export default App
