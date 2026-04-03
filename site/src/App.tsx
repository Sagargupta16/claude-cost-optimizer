import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import Home from './pages/Home'
import Calculator from './pages/Calculator'
import BadgeChecker from './pages/BadgeChecker'
import styles from './App.module.css'

function App() {
  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/calculator" element={<Calculator />} />
          <Route path="/badge" element={<BadgeChecker />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}

export default App
