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
import { UserDetailPage } from './pages/admin/UserDetailPage'
import { PendingSuppliersPage } from './pages/admin/PendingSuppliersPage'
import { ImpersonationPage } from './pages/admin/ImpersonationPage'
import { AuditLogPage } from './pages/admin/AuditLogPage'
import { ChartOfAccountsPage } from './pages/accounting/ChartOfAccountsPage'
import { PeriodsPage } from './pages/accounting/PeriodsPage'
import { ManualJournalPage } from './pages/accounting/ManualJournalPage'
import { ReceiptsPage } from './pages/accounting/ReceiptsPage'
import { DeferredTermsPage } from './pages/accounting/DeferredTermsPage'
import { ReportsIndexPage } from './pages/accounting/ReportsIndexPage'
import { TrialBalancePage } from './pages/accounting/reports/TrialBalancePage'
import { IncomeStatementPage } from './pages/accounting/reports/IncomeStatementPage'
import { BalanceSheetPage } from './pages/accounting/reports/BalanceSheetPage'
import { CashFlowPage } from './pages/accounting/reports/CashFlowPage'
import { GeneralLedgerPage } from './pages/accounting/reports/GeneralLedgerPage'
import { CatalogPage } from './pages/commerce/CatalogPage'
import { CartPage } from './pages/commerce/CartPage'
import { OrdersPage } from './pages/commerce/OrdersPage'
import { OrderDetailPage } from './pages/commerce/OrderDetailPage'
import { RfqPage } from './pages/commerce/RfqPage'
import { RfqDetailPage } from './pages/commerce/RfqDetailPage'
import { ProductsPage } from './pages/inventory/ProductsPage'
import { OffersPage } from './pages/inventory/OffersPage'
import { StockPage } from './pages/inventory/StockPage'
import { TransfersPage } from './pages/inventory/TransfersPage'
import { ShortagesPage } from './pages/inventory/ShortagesPage'

const FINANCE = ['admin', 'staff']

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterCustomerPage />} />
      <Route path="/register/supplier" element={<RegisterSupplierPage />} />
      <Route path="/otp" element={<OtpVerifyPage />} />

      <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
        <Route path="/" element={<HomePage />} />
        <Route path="/2fa" element={<TotpEnrollPage />} />

        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/orders/:id" element={<OrderDetailPage />} />
        <Route path="/rfq" element={<RfqPage />} />
        <Route path="/rfq/:id" element={<RfqDetailPage />} />

        <Route path="/admin/users" element={<ProtectedRoute roles={FINANCE}><UsersPage /></ProtectedRoute>} />
        <Route path="/admin/users/:id" element={<ProtectedRoute roles={FINANCE}><UserDetailPage /></ProtectedRoute>} />
        <Route path="/admin/suppliers/pending" element={<ProtectedRoute roles={FINANCE}><PendingSuppliersPage /></ProtectedRoute>} />
        <Route path="/admin/impersonation" element={<ProtectedRoute roles={FINANCE}><ImpersonationPage /></ProtectedRoute>} />
        <Route path="/admin/audit" element={<ProtectedRoute roles={['admin']}><AuditLogPage /></ProtectedRoute>} />

        <Route path="/accounting/chart" element={<ProtectedRoute roles={FINANCE}><ChartOfAccountsPage /></ProtectedRoute>} />
        <Route path="/accounting/periods" element={<ProtectedRoute roles={FINANCE}><PeriodsPage /></ProtectedRoute>} />
        <Route path="/accounting/journal/manual" element={<ProtectedRoute roles={FINANCE}><ManualJournalPage /></ProtectedRoute>} />
        <Route path="/accounting/receipts" element={<ProtectedRoute roles={FINANCE}><ReceiptsPage /></ProtectedRoute>} />
        <Route path="/accounting/deferred" element={<ProtectedRoute roles={FINANCE}><DeferredTermsPage /></ProtectedRoute>} />
        <Route path="/accounting/reports" element={<ProtectedRoute roles={FINANCE}><ReportsIndexPage /></ProtectedRoute>} />
        <Route path="/accounting/reports/trial-balance" element={<ProtectedRoute roles={FINANCE}><TrialBalancePage /></ProtectedRoute>} />
        <Route path="/accounting/reports/income-statement" element={<ProtectedRoute roles={FINANCE}><IncomeStatementPage /></ProtectedRoute>} />
        <Route path="/accounting/reports/balance-sheet" element={<ProtectedRoute roles={FINANCE}><BalanceSheetPage /></ProtectedRoute>} />
        <Route path="/accounting/reports/cash-flow" element={<ProtectedRoute roles={FINANCE}><CashFlowPage /></ProtectedRoute>} />
        <Route path="/accounting/reports/general-ledger" element={<ProtectedRoute roles={FINANCE}><GeneralLedgerPage /></ProtectedRoute>} />

        <Route path="/inventory/products" element={<ProtectedRoute roles={FINANCE}><ProductsPage /></ProtectedRoute>} />
        <Route path="/inventory/offers" element={<ProtectedRoute roles={['supplier']}><OffersPage /></ProtectedRoute>} />
        <Route path="/inventory/stock" element={<StockPage />} />
        <Route path="/inventory/transfers" element={<ProtectedRoute roles={FINANCE}><TransfersPage /></ProtectedRoute>} />
        <Route path="/inventory/shortages" element={<ProtectedRoute roles={FINANCE}><ShortagesPage /></ProtectedRoute>} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
