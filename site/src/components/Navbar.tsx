import { NavLink } from 'react-router-dom'
import styles from './Navbar.module.css'

function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.inner}>
        <NavLink to="/" className={styles.logo}>
          Claude Cost Optimizer
        </NavLink>
        <div className={styles.links}>
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              isActive ? `${styles.link} ${styles.active}` : styles.link
            }
          >
            Home
          </NavLink>
          <NavLink
            to="/calculator"
            className={({ isActive }) =>
              isActive ? `${styles.link} ${styles.active}` : styles.link
            }
          >
            Calculator
          </NavLink>
          <NavLink
            to="/badge"
            className={({ isActive }) =>
              isActive ? `${styles.link} ${styles.active}` : styles.link
            }
          >
            Badge Checker
          </NavLink>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.link}
          >
            GitHub
          </a>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
