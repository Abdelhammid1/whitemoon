import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layouts/AppShell'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { RootRoute } from './auth/RootRoute'
import { UserGuidePage } from './pages/UserGuidePage'
import { AssistantPage } from './pages/AssistantPage'
import { KnowledgeGapsPage } from './pages/KnowledgeGapsPage'
import { HomePage } from './pages/HomePage'
import { OnboardingPage } from './pages/OnboardingPage'
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
import { ProductDetailPage } from './pages/commerce/ProductDetailPage'
import { SupplierOrdersPage } from './pages/commerce/SupplierOrdersPage'
import { CartPage } from './pages/commerce/CartPage'
import { OrdersPage } from './pages/commerce/OrdersPage'
import { AdminOrdersPage } from './pages/commerce/AdminOrdersPage'
import { OrderDetailPage } from './pages/commerce/OrderDetailPage'
import { RfqPage } from './pages/commerce/RfqPage'
import { RfqDetailPage } from './pages/commerce/RfqDetailPage'
import { StatementPage } from './pages/commerce/StatementPage'
import { CreditPage } from './pages/credit/CreditPage'
import { TierSettingsPage } from './pages/credit/TierSettingsPage'
import { PaymentsPage } from './pages/credit/PaymentsPage'
import { UploadReceiptPage } from './pages/credit/UploadReceiptPage'
import { DunningPage } from './pages/credit/DunningPage'
import { CompliancePage } from './pages/compliance/CompliancePage'
import { PartnersPage } from './pages/partners/PartnersPage'
import { PartnerDetailPage } from './pages/partners/PartnerDetailPage'
import { ProductionPage } from './pages/production/ProductionPage'
import { ProductionDetailPage } from './pages/production/ProductionDetailPage'
import { PosPage } from './pages/pos/PosPage'
import { PosSalesPage } from './pages/pos/PosSalesPage'
import { PosSettlePage } from './pages/pos/PosSettlePage'
import { LogisticsPage } from './pages/logistics/LogisticsPage'
import { ShipmentsPage } from './pages/logistics/ShipmentsPage'
import { TrackingPage } from './pages/logistics/TrackingPage'
import { DeliveryConfirmPage } from './pages/logistics/DeliveryConfirmPage'
import { ChatPage } from './pages/comm/ChatPage'
import { ChatThreadPage } from './pages/comm/ChatThreadPage'
import { ModerationPage } from './pages/comm/ModerationPage'
import { BiDashboardPage } from './pages/bi/BiDashboardPage'
import { NotificationsPage } from './pages/notifications/NotificationsPage'
import { ProductsPage } from './pages/inventory/ProductsPage'
import { ProductFormPage } from './pages/inventory/ProductFormPage'
import { OffersPage } from './pages/inventory/OffersPage'
import { StockPage } from './pages/inventory/StockPage'
import { ReorderAlertsPage } from './pages/inventory/ReorderAlertsPage'
import { CategoriesPage } from './pages/inventory/CategoriesPage'
import { TransfersPage } from './pages/inventory/TransfersPage'
import { ShortagesPage } from './pages/inventory/ShortagesPage'

const FINANCE = ['admin', 'staff']

export function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRoute />} />
      {/* Standalone page but auth-gated: the guide exposes the permission matrix,
          internal routes table and ops procedures, so it is not public. */}
      <Route path="/guide" element={<ProtectedRoute><UserGuidePage /></ProtectedRoute>} />
      {/* Admin AI assistant — standalone full page, admin-only (assistant.use). */}
      <Route path="/assistant" element={<ProtectedRoute roles={['admin']}><AssistantPage /></ProtectedRoute>} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterCustomerPage />} />
      <Route path="/register/supplier" element={<RegisterSupplierPage />} />
      <Route path="/otp" element={<OtpVerifyPage />} />

      <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
        <Route path="/home" element={<HomePage />} />
        <Route path="/start" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
        <Route path="/2fa" element={<TotpEnrollPage />} />

        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/catalog/:id" element={<ProductDetailPage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/admin/orders" element={<ProtectedRoute roles={FINANCE}><AdminOrdersPage /></ProtectedRoute>} />
        <Route path="/orders/:id" element={<OrderDetailPage />} />
        <Route path="/rfq" element={<RfqPage />} />
        <Route path="/rfq/:id" element={<RfqDetailPage />} />
        <Route path="/statement" element={<StatementPage />} />
        <Route path="/admin/customers/:id/statement" element={<ProtectedRoute roles={FINANCE}><StatementPage /></ProtectedRoute>} />
        <Route path="/pay/receipt" element={<UploadReceiptPage />} />
        <Route path="/supplier/orders" element={<ProtectedRoute roles={['supplier']}><SupplierOrdersPage /></ProtectedRoute>} />

        <Route path="/admin/users" element={<ProtectedRoute roles={FINANCE}><UsersPage /></ProtectedRoute>} />
        <Route path="/admin/users/:id" element={<ProtectedRoute roles={FINANCE}><UserDetailPage /></ProtectedRoute>} />
        <Route path="/admin/suppliers/pending" element={<ProtectedRoute roles={FINANCE}><PendingSuppliersPage /></ProtectedRoute>} />
        <Route path="/admin/impersonation" element={<ProtectedRoute roles={FINANCE}><ImpersonationPage /></ProtectedRoute>} />
        <Route path="/admin/audit" element={<ProtectedRoute roles={['admin']}><AuditLogPage /></ProtectedRoute>} />
        <Route path="/assistant/gaps" element={<ProtectedRoute roles={['admin']}><KnowledgeGapsPage /></ProtectedRoute>} />

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

        <Route path="/inventory/categories" element={<ProtectedRoute roles={FINANCE}><CategoriesPage /></ProtectedRoute>} />
        <Route path="/inventory/products" element={<ProtectedRoute roles={FINANCE}><ProductsPage /></ProtectedRoute>} />
        <Route path="/inventory/products/new" element={<ProtectedRoute roles={FINANCE}><ProductFormPage /></ProtectedRoute>} />
        <Route path="/inventory/products/:id/edit" element={<ProtectedRoute roles={FINANCE}><ProductFormPage /></ProtectedRoute>} />
        <Route path="/inventory/offers" element={<ProtectedRoute roles={['supplier']}><OffersPage /></ProtectedRoute>} />
        <Route path="/inventory/stock" element={<StockPage />} />
        <Route path="/inventory/reorder" element={<ProtectedRoute roles={FINANCE}><ReorderAlertsPage /></ProtectedRoute>} />
        <Route path="/inventory/transfers" element={<ProtectedRoute roles={FINANCE}><TransfersPage /></ProtectedRoute>} />
        <Route path="/inventory/shortages" element={<ProtectedRoute roles={['admin']}><ShortagesPage /></ProtectedRoute>} />

        <Route path="/credit" element={<ProtectedRoute roles={FINANCE}><CreditPage /></ProtectedRoute>} />
        <Route path="/credit/dunning" element={<ProtectedRoute roles={FINANCE}><DunningPage /></ProtectedRoute>} />
        <Route path="/credit/tiers" element={<ProtectedRoute roles={FINANCE}><TierSettingsPage /></ProtectedRoute>} />
        <Route path="/credit/payments" element={<ProtectedRoute roles={FINANCE}><PaymentsPage /></ProtectedRoute>} />
        <Route path="/compliance" element={<ProtectedRoute roles={FINANCE}><CompliancePage /></ProtectedRoute>} />

        <Route path="/partners" element={<ProtectedRoute roles={FINANCE}><PartnersPage /></ProtectedRoute>} />
        <Route path="/partners/:id" element={<ProtectedRoute roles={FINANCE}><PartnerDetailPage /></ProtectedRoute>} />
        <Route path="/production" element={<ProtectedRoute roles={FINANCE}><ProductionPage /></ProtectedRoute>} />
        <Route path="/production/:id" element={<ProtectedRoute roles={FINANCE}><ProductionDetailPage /></ProtectedRoute>} />

        <Route path="/pos" element={<ProtectedRoute roles={['agent', 'branch', 'staff', 'admin']}><PosPage /></ProtectedRoute>} />
        <Route path="/pos/sales" element={<ProtectedRoute roles={['agent', 'branch', 'staff', 'admin']}><PosSalesPage /></ProtectedRoute>} />
        <Route path="/pos/settle" element={<ProtectedRoute roles={FINANCE}><PosSettlePage /></ProtectedRoute>} />

        <Route path="/logistics" element={<ProtectedRoute roles={FINANCE}><LogisticsPage /></ProtectedRoute>} />
        <Route path="/logistics/shipments" element={<ProtectedRoute roles={FINANCE}><ShipmentsPage /></ProtectedRoute>} />
        <Route path="/logistics/deliver" element={<ProtectedRoute roles={FINANCE}><DeliveryConfirmPage /></ProtectedRoute>} />
        <Route path="/orders/:id/shipment" element={<TrackingPage />} />

        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:id" element={<ChatThreadPage />} />
        <Route path="/comm/moderation" element={<ProtectedRoute roles={FINANCE}><ModerationPage /></ProtectedRoute>} />

        <Route path="/dashboard" element={<ProtectedRoute roles={FINANCE}><BiDashboardPage /></ProtectedRoute>} />
        <Route path="/notifications" element={<NotificationsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
