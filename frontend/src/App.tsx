import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { Provider } from 'react-redux';
import { store } from './store';
import Login from './pages/Login';
import LayoutPage from './pages/Layout';
import Dashboard from './pages/Dashboard';
import DemandList from './pages/demand/DemandList';
import PositionList from './pages/position/PositionList';
import CandidateList from './pages/candidate/CandidateList';
import CandidateDetail from './pages/candidate/CandidateDetail';
import InterviewList from './pages/interview/InterviewList';
import OfferList from './pages/offer/OfferList';
import OnboardingList from './pages/onboarding/OnboardingList';
import TalentPool from './pages/talent/TalentPool';
import ResumeList from './pages/resume/ResumeList';
import InvitationCenter from './pages/invitation/InvitationCenter';
import ScreeningList from './pages/screening/ScreeningList';
import NotificationList from './pages/notification/NotificationList';
import ProcessManagement from './pages/settings/ProcessManagement';
import StageConfig from './pages/settings/StageConfig';
import ScoringRules from './pages/settings/ScoringRules';
import DataDictionary from './pages/settings/DataDictionary';
import CompanySettings from './pages/settings/CompanySettings';
import AccountSettings from './pages/settings/AccountSettings';
import './App.css';

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('token');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

function App() {
  return (
    <Provider store={store}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#667eea',
            borderRadius: 8,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          },
        }}
      >
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            
            <Route path="/" element={
              <PrivateRoute>
                <LayoutPage />
              </PrivateRoute>
            }>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="demands" element={<DemandList />} />
              <Route path="positions" element={<PositionList />} />
              <Route path="candidates" element={<CandidateList />} />
              <Route path="candidates/:id" element={<CandidateDetail />} />
              <Route path="screenings" element={<ScreeningList />} />
              <Route path="interviews" element={<InterviewList />} />
              <Route path="offers" element={<OfferList />} />
              <Route path="onboardings" element={<OnboardingList />} />
              <Route path="talent-pool" element={<TalentPool />} />
              <Route path="my-resumes" element={<ResumeList />} />
              <Route path="invitations" element={<InvitationCenter />} />
              <Route path="notifications" element={<NotificationList />} />
              <Route path="settings/account" element={<AccountSettings />} />
              <Route path="settings/process" element={<ProcessManagement />} />
              <Route path="settings/stage" element={<StageConfig />} />
              <Route path="settings/scoring" element={<ScoringRules />} />
              <Route path="settings/dictionary" element={<DataDictionary />} />
              <Route path="settings/company" element={<CompanySettings />} />
            </Route>
            
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </Provider>
  );
}

export default App;
