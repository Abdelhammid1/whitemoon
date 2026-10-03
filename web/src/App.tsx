import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layouts/AppShell'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterCustomerPage } from './pages/auth/RegisterCustomerPage'
import { RegisterSupplierPage } from './pages/auth/RegisterSupplierPage'
import { OtpVerifyPage } from './pages/auth/OtpVerifyPage'
import { TotpEnrollPage } from './pages/auth/TotpEnrollPage'
import { UsersPage } from './pages/admin/UsersPage'
import { PendingSuppliersPage } from './pages/admin/PendingSuppliersPage'
import { ImpersonationPage } from './pages/admin/ImpersonationPage'
import { PeriodsPage } from './pages/accounting/PeriodsPage'
import { ManualJournalPage } from './pages/accounting/ManualJournalPage'
import { ReceiptsPage } from './pages/accounting/ReceiptsPage'
import { DeferredTermsPage } from './pages/accounting/DeferredTermsPage'
import { TrialBalancePage } from './pages/accounting/reports/TrialBalancePage'
import { IncomeStatementPage } from './pages/accounting/reports/IncomeStatementPage'
import { BalanceSheetPage } from './pages/accounting/reports/BalanceSheetPage'
import { CashFlowPage } from './pages/accounting/reports/CashFlowPage'
import { GeneralLedgerPage } from './pages/accounting/reports/GeneralLedgerPage'

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterCustomerPage />} />
      <Route path="/register/supplier" element={<RegisterSupplierPage />} />
      <Route path="/otp" element={<OtpVerifyPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<HomePage />} />
        <Route path="/2fa" element={<TotpEnrollPage />} />

        <Route path="/admin/users" element={<UsersPage />} />
        <Route
          path="/admin/suppliers/pending"
          element={<PendingSuppliersPage />}
        />
        <Route path="/admin/impersonation" element={<ImpersonationPage />} />

        <Route path="/accounting/periods" element={<PeriodsPage />} />
        <Route
          path="/accounting/journal/manual"
          element={<ManualJournalPage />}
        />
        <Route path="/accounting/receipts" element={<ReceiptsPage />} />
        <Route path="/accounting/deferred" element={<DeferredTermsPage />} />
        <Route
          path="/accounting/reports/trial-balance"
          element={<TrialBalancePage />}
        />
        <Route
          path="/accounting/reports/income-statement"
          element={<IncomeStatementPage />}
        />
        <Route
          path="/accounting/reports/balance-sheet"
          element={<BalanceSheetPage />}
        />
        <Route
          path="/accounting/reports/cash-flow"
          element={<CashFlowPage />}
        />
        <Route
          path="/accounting/reports/general-ledger"
          element={<GeneralLedgerPage />}
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
