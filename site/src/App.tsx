import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import Home from './pages/Home'
import styles from './App.module.css'

function App() {
  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <Routes>
          <Route path="/*" element={<Home />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}

export default App
