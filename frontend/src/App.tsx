import { Navigate, Route, Routes } from "react-router-dom"

import AppShell from "./components/layout/AppShell"

import MerchantOverview from "./features/merchant/MerchantOverview"
import MerchantRecoveryCases from "./features/merchant/MerchantRecoveryCases"
import MerchantCaseDetail from "./features/merchant/MerchantCaseDetail"
import MerchantEscalations from "./features/merchant/MerchantEscalations"
import MerchantBatches from "./features/merchant/MerchantBatches"
import MerchantBatchDetail from "./features/merchant/MerchantBatchDetail"
import DeveloperOverview from "./features/developer/DeveloperOverview"
import DeveloperEventExplorer from "./features/developer/DeveloperEventExplorer"
import DeveloperAIDecisions from "./features/developer/DeveloperAIDecisions"
import DeveloperAIDecisionDetail from "./features/developer/DeveloperAIDecisionDetail"
import DeveloperExecutions from "./features/developer/DeveloperExecutions"
import DeveloperSystemHealth from "./features/developer/DeveloperSystemHealth"

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to="/merchant" replace />} />

        <Route path="/merchant" element={<MerchantOverview />} />
        <Route path="/merchant/cases" element={<MerchantRecoveryCases />} />
        <Route path="/merchant/cases/:caseId" element={<MerchantCaseDetail />} />
        <Route path="/merchant/escalations" element={<MerchantEscalations />} />
        <Route path="/merchant/batches" element={<MerchantBatches />} />
        <Route path="/merchant/batches/:batchId" element={<MerchantBatchDetail />} />

        <Route path="/developer" element={<DeveloperOverview />} />
        <Route path="/developer/events" element={<DeveloperEventExplorer />} />
        <Route path="/developer/decisions" element={<DeveloperAIDecisions />} />
        <Route path="/developer/decisions/:caseId" element={<DeveloperAIDecisionDetail />} />
        <Route path="/developer/executions" element={<DeveloperExecutions />} />

        {/* These views use the same persisted case/escalation records as the merchant portal. */}
        <Route path="/developer/cases" element={<Navigate to="/merchant/cases" replace />} />
        <Route path="/developer/escalations" element={<Navigate to="/merchant/escalations" replace />} />
        <Route path="/developer/health" element={<DeveloperSystemHealth />} />

        <Route path="*" element={<Navigate to="/merchant" replace />} />
      </Route>
    </Routes>
  )
}

export default App
