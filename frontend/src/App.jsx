import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import AppLayout from './components/AppLayout'
import AdminLayout from './components/AdminLayout'
import AuthLayout from './components/AuthLayout'
import useGameInfo from './hooks/useGameInfo'

import MainPage from './pages/MainPage'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import LeaderboardPage from './pages/LeaderboardPage'
import StorePage from './pages/StorePage'
import QuizPage from './pages/QuizPage'
import LobbyPage from './pages/LobbyPage'
import RegisterPage from './pages/RegisterPage'
import JoinPage from './pages/JoinPage'
import VictoryPage from './pages/VictoryPage'
import DefeatPage from './pages/DefeatPage'
import NotificationsPage from './pages/NotificationsPage'
import PlayerProfilePage from './pages/PlayerProfilePage'

import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminCompetitionPage from './pages/admin/AdminCompetitionPage'
import AdminPlayersPage from './pages/admin/AdminPlayersPage'
import AdminPlayerDetailPage from './pages/admin/AdminPlayerDetailPage'
import AdminAttacksPage from './pages/admin/AdminAttacksPage'
import AdminQuizPage from './pages/admin/AdminQuizPage'
import AdminStorePage from './pages/admin/AdminStorePage'
import AdminLedgerPage from './pages/admin/AdminLedgerPage'
import AdminNotificationsPage from './pages/admin/AdminNotificationsPage'
import AdminSettingsPage from './pages/admin/AdminSettingsPage'

function EntryRoute() {
  const alreadySeen = sessionStorage.getItem('mainPageSeen') === '1'
  if (alreadySeen) return <Navigate to="/lobby" replace />
  return <MainPage />
}

function GameRoutes() {
  const { gameInfo, loading, error } = useGameInfo()
  const seasonText = gameInfo?.current_season

  return (
    <Routes>
      {/* ── Entry / Main Page ── */}
      <Route path="/" element={<EntryRoute />} />

      {/* ── Auth pages (no protection) ── */}
      <Route
        path="/login"
        element={
          <AuthLayout>
            <LoginPage />
          </AuthLayout>
        }
      />
      <Route
        path="/register"
        element={
          <AuthLayout>
            <RegisterPage />
          </AuthLayout>
        }
      />
      <Route
        path="/join"
        element={
          <AuthLayout showLogo={false}>
            <JoinPage />
          </AuthLayout>
        }
      />

      {/* ── Protected game pages ── */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="home" seasonText={seasonText}>
              <DashboardPage gameInfo={gameInfo} loading={loading} error={error} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/leaderboard"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="leaderboard" seasonText={seasonText}>
              <LeaderboardPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/store"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="shop" seasonText={seasonText}>
              <StorePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/quiz"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="battle" seasonText="جلسة الأسئلة المباشرة">
              <QuizPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/battle/victory"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="" seasonText={seasonText}>
              <VictoryPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/battle/defeat"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="" seasonText={seasonText}>
              <DefeatPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="" seasonText={seasonText}>
              <NotificationsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/players/:membershipId"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="leaderboard" seasonText={seasonText}>
              <PlayerProfilePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* ── Admin Panel ── */}
      <Route path="/admin" element={<AdminRoute><AdminLayout /></AdminRoute>}>
        <Route index element={<AdminDashboardPage />} />
        <Route path="competition" element={<AdminCompetitionPage />} />
        <Route path="players" element={<AdminPlayersPage />} />
        <Route path="players/:membershipId" element={<AdminPlayerDetailPage />} />
        <Route path="attacks" element={<AdminAttacksPage />} />
        <Route path="quiz" element={<AdminQuizPage />} />
        <Route path="store" element={<AdminStorePage />} />
        <Route path="ledger" element={<AdminLedgerPage />} />
        <Route path="notifications" element={<AdminNotificationsPage />} />
        <Route path="settings" element={<AdminSettingsPage />} />
      </Route>

      {/* ── Lobby — standalone dark immersive page ── */}
      <Route path="/lobby" element={<LobbyPage />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <GameRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}
