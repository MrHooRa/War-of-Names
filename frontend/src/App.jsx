import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import AppLayout from './components/AppLayout'
import AdminLayout from './components/AdminLayout'
import AuthLayout from './components/AuthLayout'

import MainPage from './pages/MainPage'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import LeaderboardPage from './pages/LeaderboardPage'
import StorePage from './pages/StorePage'
import QuizPage from './pages/QuizPage'
import LobbyPage from './pages/LobbyPage'
import RegisterPage from './pages/RegisterPage'
import JoinPage from './pages/JoinPage'
import InviteLinkPage from './pages/InviteLinkPage'
import VictoryPage from './pages/VictoryPage'
import DefeatPage from './pages/DefeatPage'
import NotificationsPage from './pages/NotificationsPage'
import PlayerProfilePage from './pages/PlayerProfilePage'
import AccountSettingsPage from './pages/AccountSettingsPage'
import RulesPage from './pages/RulesPage'
import NotFoundPage from './pages/NotFoundPage'

import { AdminCompetitionProvider } from './context/AdminCompetitionContext'

import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminCompetitionPage from './pages/admin/AdminCompetitionPage'
import AdminAccountsPage from './pages/admin/AdminAccountsPage'
import AdminMembersPage from './pages/admin/AdminMembersPage'
import AdminPlayerDetailPage from './pages/admin/AdminPlayerDetailPage'
import AdminSeasonsPage from './pages/admin/AdminSeasonsPage'
import AdminAttacksPage from './pages/admin/AdminAttacksPage'
import AdminQuizPage from './pages/admin/AdminQuizPage'
import AdminStorePage from './pages/admin/AdminStorePage'
import AdminLedgerPage from './pages/admin/AdminLedgerPage'
import AdminNotificationsPage from './pages/admin/AdminNotificationsPage'
import AdminSettingsPage from './pages/admin/AdminSettingsPage'
import AdminPlatformSettingsPage from './pages/admin/AdminPlatformSettingsPage'

function useCaptureRef() {
  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get('ref')
    if (ref) {
      try { sessionStorage.setItem('won_landing_ref', ref) } catch {}
    }
  }, [])
}

function GameRoutes() {
  useCaptureRef()
  return (
    <Routes>
      {/* ── Entry / Main Page (auth-aware gateway) ── */}
      <Route path="/" element={<MainPage />} />

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

      {/* ── Invite link (public, handles auth redirect internally) ── */}
      <Route path="/invite/:token" element={<InviteLinkPage />} />

      {/* ── Protected game pages ── */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="home">
              <DashboardPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/leaderboard"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="leaderboard">
              <LeaderboardPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/store"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="shop">
              <StorePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/quiz"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="battle">
              <QuizPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/battle/victory"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="">
              <VictoryPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/battle/defeat"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="">
              <DefeatPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="">
              <NotificationsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/players/:membershipId"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="leaderboard">
              <PlayerProfilePage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/account"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="profile">
              <AccountSettingsPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/rules"
        element={
          <ProtectedRoute>
            <AppLayout activeItem="rules">
              <RulesPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* ── Admin Panel ── */}
      <Route path="/admin" element={<AdminRoute><AdminCompetitionProvider><AdminLayout /></AdminCompetitionProvider></AdminRoute>}>
        {/* Platform level */}
        <Route index element={<AdminDashboardPage />} />
        <Route path="accounts" element={<AdminAccountsPage />} />
        <Route path="platform-settings" element={<AdminPlatformSettingsPage />} />
        {/* Competition level */}
        <Route path="competition" element={<AdminCompetitionPage />} />
        <Route path="members" element={<AdminMembersPage />} />
        <Route path="members/:membershipId" element={<AdminPlayerDetailPage />} />
        <Route path="seasons" element={<AdminSeasonsPage />} />
        <Route path="attacks" element={<AdminAttacksPage />} />
        <Route path="quiz" element={<AdminQuizPage />} />
        <Route path="store" element={<AdminStorePage />} />
        <Route path="ledger" element={<AdminLedgerPage />} />
        <Route path="notifications" element={<AdminNotificationsPage />} />
        <Route path="settings" element={<AdminSettingsPage />} />
      </Route>

      {/* ── Lobby — standalone dark immersive page ── */}
      <Route path="/lobby" element={<LobbyPage />} />

      {/* ── Catch-all 404 ── */}
      <Route path="*" element={<NotFoundPage />} />
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
