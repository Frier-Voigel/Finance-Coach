import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { ToastProvider } from './components/Toast';
import UploadPage from './features/upload/UploadPage';
import ReviewPage from './features/review/ReviewPage';
import SubscriptionsPage from './features/subscriptions/SubscriptionsPage';
import ProfilePage from './features/profile/ProfilePage';
import GoalsPage from './features/goals/GoalsPage';
import WhatIfPage from './features/whatif/WhatIfPage';
import NudgesPage from './features/nudges/NudgesPage';
import ReportPage from './features/report/ReportPage';

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/upload" replace />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="transactions" element={<Navigate to="/review" replace />} />
          <Route path="subscriptions" element={<SubscriptionsPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="goals" element={<GoalsPage />} />
          <Route path="whatif" element={<WhatIfPage />} />
          <Route path="nudges" element={<NudgesPage />} />
          <Route path="report" element={<ReportPage />} />
          <Route path="*" element={<Navigate to="/upload" replace />} />
        </Route>
      </Routes>
    </ToastProvider>
  );
}
