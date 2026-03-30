import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'

import ErrorBoundary from './components/ErrorBoundary'
import ConsentBanner from './components/ConsentBanner'
import { trackPageView } from './lib/analytics'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import OwnerRoute from './components/OwnerRoute'
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
import TermsPage from './pages/TermsPage'
import PrivacyPage from './pages/PrivacyPage'
import NotFoundPage from './pages/NotFoundPage'

import { AdminCompetitionProvider } from './context/AdminCompetitionContext'

// ── Lazy-loaded admin pages (code-split into separate chunk) ──
const OwnerLayout = lazy(() => import('./pages/owner/OwnerLayout'))
const OwnerDashboardPage = lazy(() => import('./pages/owner/OwnerDashboardPage'))

const AdminDashboardPage = lazy(() => import('./pages/admin/AdminDashboardPage'))
const AdminCompetitionPage = lazy(() => import('./pages/admin/AdminCompetitionPage'))
const AdminAccountsPage = lazy(() => import('./pages/admin/AdminAccountsPage'))
const AdminMembersPage = lazy(() => import('./pages/admin/AdminMembersPage'))
const AdminPlayerDetailPage = lazy(() => import('./pages/admin/AdminPlayerDetailPage'))
const AdminSeasonsPage = lazy(() => import('./pages/admin/AdminSeasonsPage'))
const AdminAttacksPage = lazy(() => import('./pages/admin/AdminAttacksPage'))
const AdminQuizPage = lazy(() => import('./pages/admin/AdminQuizPage'))
const AdminStorePage = lazy(() => import('./pages/admin/AdminStorePage'))
const AdminLedgerPage = lazy(() => import('./pages/admin/AdminLedgerPage'))
const AdminNotificationsPage = lazy(() => import('./pages/admin/AdminNotificationsPage'))
const AdminSettingsPage = lazy(() => import('./pages/admin/AdminSettingsPage'))
const AdminPlatformSettingsPage = lazy(() => import('./pages/admin/AdminPlatformSettingsPage'))

function PageTracker() {
  const location = useLocation()
  useEffect(() => {
    trackPageView(location.pathname)
  }, [location.pathname])
  return null
}

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

      {/* ── Public legal pages (no auth required) ── */}
      <Route path="/terms" element={<TermsPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />

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
        path="/competitions/:competitionId/leaderboard"
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
        path="/competitions/:competitionId/players/:membershipId"
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

      {/* ── Admin Panel (lazy-loaded) ── */}
      <Route path="/admin" element={<AdminRoute><AdminCompetitionProvider><Suspense fallback={null}><AdminLayout /></Suspense></AdminCompetitionProvider></AdminRoute>}>
        {/* Platform level */}
        <Route index element={<Suspense fallback={null}><AdminDashboardPage /></Suspense>} />
        <Route path="accounts" element={<Suspense fallback={null}><AdminAccountsPage /></Suspense>} />
        <Route path="platform-settings" element={<Suspense fallback={null}><AdminPlatformSettingsPage /></Suspense>} />
        {/* Competition level */}
        <Route path="competition" element={<Suspense fallback={null}><AdminCompetitionPage /></Suspense>} />
        <Route path="members" element={<Suspense fallback={null}><AdminMembersPage /></Suspense>} />
        <Route path="members/:membershipId" element={<Suspense fallback={null}><AdminPlayerDetailPage /></Suspense>} />
        <Route path="seasons" element={<Suspense fallback={null}><AdminSeasonsPage /></Suspense>} />
        <Route path="attacks" element={<Suspense fallback={null}><AdminAttacksPage /></Suspense>} />
        <Route path="quiz" element={<Suspense fallback={null}><AdminQuizPage /></Suspense>} />
        <Route path="store" element={<Suspense fallback={null}><AdminStorePage /></Suspense>} />
        <Route path="ledger" element={<Suspense fallback={null}><AdminLedgerPage /></Suspense>} />
        <Route path="notifications" element={<Suspense fallback={null}><AdminNotificationsPage /></Suspense>} />
        <Route path="settings" element={<Suspense fallback={null}><AdminSettingsPage /></Suspense>} />
      </Route>

      {/* ── Owner Panel (lazy-loaded) ── */}
      <Route path="/owner" element={<OwnerRoute><Suspense fallback={null}><OwnerLayout /></Suspense></OwnerRoute>}>
        <Route index element={<Suspense fallback={null}><OwnerDashboardPage /></Suspense>} />
      </Route>

      {/* ── Lobby — standalone dark immersive page ── */}
      <Route path="/lobby" element={<ProtectedRoute><LobbyPage /></ProtectedRoute>} />

      {/* ── Catch-all 404 ── */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <PageTracker />
          <GameRoutes />
          <ConsentBanner />
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}
