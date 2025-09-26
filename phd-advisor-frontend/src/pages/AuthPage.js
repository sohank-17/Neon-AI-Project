import React, { useState } from 'react';
import Login from '../components/Login';
import Signup from '../components/Signup';
import EmailVerification from '../components/EmailVerification';

const AuthPage = ({ onAuthSuccess }) => {
  const [currentView, setCurrentView] = useState('login'); // 'login', 'signup', 'verification'
  const [verificationEmail, setVerificationEmail] = useState('');

  const handleNavigateToLogin = () => setCurrentView('login');
  const handleNavigateToSignup = () => setCurrentView('signup');
  
  const handleNavigateToVerification = (email) => {
    setVerificationEmail(email);
    setCurrentView('verification');
  };

  const handleVerificationSuccess = (user, token) => {
    onAuthSuccess(user, token);
  };

  const handleBackToSignup = () => {
    setCurrentView('signup');
    setVerificationEmail('');
  };

  return (
    <>
      {currentView === 'login' && (
        <Login 
          onNavigateToSignup={handleNavigateToSignup}
          onNavigateToHome={onAuthSuccess}
          onNavigateToVerification={handleNavigateToVerification}
        />
      )}
      
      {currentView === 'signup' && (
        <Signup 
          onNavigateToLogin={handleNavigateToLogin}
          onNavigateToHome={onAuthSuccess}
          onNavigateToVerification={handleNavigateToVerification}
        />
      )}
      
      {currentView === 'verification' && (
        <EmailVerification
          email={verificationEmail}
          onVerificationSuccess={handleVerificationSuccess}
          onBackToSignup={handleBackToSignup}
        />
      )}
    </>
  );
};

export default AuthPage;