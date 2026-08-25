import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import LandingPage from './pages/LandingPage'
import WarRoomPage from './pages/WarRoomPage'
import { SmoothScroll } from './motion/SmoothScroll'

export default function App() {
  const location = useLocation()

  return (
    <SmoothScroll>
      <AnimatePresence mode="wait">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        >
          <Routes location={location}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/war-room" element={<WarRoomShell />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </motion.div>
      </AnimatePresence>
    </SmoothScroll>
  )
}

function WarRoomShell() {
  return (
    <div className="min-h-screen bg-void">
      <WarRoomPage />
    </div>
  )
}
