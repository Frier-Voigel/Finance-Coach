import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import GoalsPage from "./features/goals/GoalsPage.jsx";
import NudgesPage from "./features/nudges/NudgesPage.jsx";
import ProfilePage from "./features/profile/ProfilePage.jsx";
import ReportPage from "./features/report/ReportPage.jsx";
import SubscriptionsPage from "./features/subscriptions/SubscriptionsPage.jsx";
import TransactionsPage from "./features/transactions/TransactionsPage.jsx";
import UploadPage from "./features/upload/UploadPage.jsx";
import VoiceDock from "./features/voice/VoiceDock.jsx";
import WhatIfPage from "./features/whatif/WhatIfPage.jsx";

// Navigation links for both Person A and Person B features
const links = [
  ["/upload", "Upload"],
  ["/transactions", "Transactions"],
  ["/subscriptions", "Subscriptions"],
  ["/profile", "Profile"],
  ["/goals", "Goals"],
  ["/whatif", "What-if"],
  ["/nudges", "Nudges"],
  ["/report", "Report"],
];

export default function App() {
  return (
    <div className="mx-auto max-w-4xl px-4 pb-48 pt-4">
      <nav className="mb-6 flex flex-wrap items-center gap-1 border-b border-slate-200 pb-3">
        <span className="mr-4 text-lg font-semibold text-emerald-700">Finance Coach</span>
        {links.map(([to, label]) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `rounded-lg px-3 py-1.5 text-sm ${
                isActive ? "bg-emerald-100 text-emerald-800 font-medium" : "text-slate-600 hover:bg-slate-100"
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route path="/" element={<Navigate to="/profile" replace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
        <Route path="/subscriptions" element={<SubscriptionsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/goals" element={<GoalsPage />} />
        <Route path="/whatif" element={<WhatIfPage />} />
        <Route path="/nudges" element={<NudgesPage />} />
        <Route path="/report" element={<ReportPage />} />
      </Routes>
      <VoiceDock />
    </div>
  );
}
