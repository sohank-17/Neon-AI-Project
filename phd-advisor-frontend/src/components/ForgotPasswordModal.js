import React, { useState } from 'react';
import { X, Mail, Lock, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react';
import '../styles/ForgotPasswordModal.css';

const ForgotPasswordModal = ({ isOpen, onClose }) => {
  const [step, setStep] = useState('email'); // 'email', 'verify', 'success'
  const [email, setEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});

  // Reset modal state when closed
  React.useEffect(() => {
    if (!isOpen) {
      setTimeout(() => {
        setStep('email');
        setEmail('');
        setResetCode('');
        setNewPassword('');
        setConfirmPassword('');
        setErrors({});
        setShowPassword(false);
        setShowConfirmPassword(false);
      }, 300);
    }
  }, [isOpen]);

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    
    // Validate email
    if (!email) {
      setErrors({ email: 'Email is required' });
      return;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
      setErrors({ email: 'Please enter a valid email address' });
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setStep('verify');
      } else {
        setErrors({ submit: data.detail || 'Failed to send reset code. Please try again.' });
      }
    } catch (error) {
      console.error('Forgot password error:', error);
      setErrors({ submit: 'Network error. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifySubmit = async (e) => {
    e.preventDefault();
    
    // Validate inputs
    const newErrors = {};
    if (!resetCode) {
      newErrors.resetCode = 'Reset code is required';
    } else if (!/^\d{6}$/.test(resetCode)) {
      newErrors.resetCode = 'Reset code must be 6 digits';
    }
    
    if (!newPassword) {
      newErrors.newPassword = 'New password is required';
    } else if (newPassword.length < 8) {
      newErrors.newPassword = 'Password must be at least 8 characters';
    }
    
    if (!confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (newPassword !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/verify-reset-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          reset_code: resetCode,
          new_password: newPassword
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setStep('success');
      } else {
        setErrors({ submit: data.detail || 'Invalid or expired reset code. Please try again.' });
      }
    } catch (error) {
      console.error('Reset verification error:', error);
      setErrors({ submit: 'Network error. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendCode = async () => {
    setIsLoading(true);
    try {
      await fetch(`${process.env.REACT_APP_API_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });
      // Show success message (always show success for security)
      setErrors({ resend: 'Code resent successfully!' });
    } catch (error) {
      setErrors({ resend: 'Failed to resend code. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        
        {/* Header */}
        <div className="modal-header">
          <h2 className="modal-title">
            {step === 'email' && 'Forgot Password'}
            {step === 'verify' && 'Enter Reset Code'}
            {step === 'success' && 'Password Reset'}
          </h2>
          <button 
            onClick={onClose} 
            className="modal-close"
            disabled={isLoading}
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="modal-content">
          
          {/* Step 1: Email Input */}
          {step === 'email' && (
            <form onSubmit={handleEmailSubmit}>
              <p className="modal-description">
                Enter your email address and we'll send you a verification code to reset your password.
              </p>
              
              <div className="form-group">
                <label htmlFor="reset-email" className="form-label">
                  Email Address
                </label>
                <div className="input-container">
                  <Mail className="input-icon" />
                  <input
                    type="email"
                    id="reset-email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (errors.email) setErrors(prev => ({ ...prev, email: '' }));
                    }}
                    className={`form-input ${errors.email ? 'error' : ''}`}
                    placeholder="Enter your email address"
                    disabled={isLoading}
                  />
                </div>
                {errors.email && (
                  <span className="error-message">{errors.email}</span>
                )}
              </div>

              {errors.submit && (
                <div className="error-alert">
                  <AlertCircle size={16} />
                  {errors.submit}
                </div>
              )}

              <button 
                type="submit" 
                className={`submit-btn ${isLoading ? 'loading' : ''}`}
                disabled={isLoading}
              >
                {isLoading ? 'Sending...' : 'Send Reset Code'}
              </button>
            </form>
          )}

          {/* Step 2: Verification Code & New Password */}
          {step === 'verify' && (
            <form onSubmit={handleVerifySubmit}>
              <p className="modal-description">
                Enter the 6-digit verification code sent to <strong>{email}</strong> and your new password.
              </p>
              
              <div className="form-group">
                <label htmlFor="reset-code" className="form-label">
                  Verification Code
                </label>
                <input
                  type="text"
                  id="reset-code"
                  value={resetCode}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                    setResetCode(value);
                    if (errors.resetCode) setErrors(prev => ({ ...prev, resetCode: '' }));
                  }}
                  className={`form-input code-input ${errors.resetCode ? 'error' : ''}`}
                  placeholder="000000"
                  maxLength="6"
                  disabled={isLoading}
                />
                {errors.resetCode && (
                  <span className="error-message">{errors.resetCode}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="new-password" className="form-label">
                  New Password
                </label>
                <div className="input-container">
                  <Lock className="input-icon" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="new-password"
                    value={newPassword}
                    onChange={(e) => {
                      setNewPassword(e.target.value);
                      if (errors.newPassword) setErrors(prev => ({ ...prev, newPassword: '' }));
                    }}
                    className={`form-input ${errors.newPassword ? 'error' : ''}`}
                    placeholder="Enter new password"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="password-toggle"
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.newPassword && (
                  <span className="error-message">{errors.newPassword}</span>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="confirm-password" className="form-label">
                  Confirm Password
                </label>
                <div className="input-container">
                  <Lock className="input-icon" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    id="confirm-password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errors.confirmPassword) setErrors(prev => ({ ...prev, confirmPassword: '' }));
                    }}
                    className={`form-input ${errors.confirmPassword ? 'error' : ''}`}
                    placeholder="Confirm new password"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="password-toggle"
                    disabled={isLoading}
                  >
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <span className="error-message">{errors.confirmPassword}</span>
                )}
              </div>

              {errors.submit && (
                <div className="error-alert">
                  <AlertCircle size={16} />
                  {errors.submit}
                </div>
              )}

              {errors.resend && (
                <div className={`resend-alert ${errors.resend.includes('successfully') ? 'success' : 'error'}`}>
                  {errors.resend.includes('successfully') ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                  {errors.resend}
                </div>
              )}

              <div className="form-actions">
                <button 
                  type="button" 
                  onClick={handleResendCode}
                  className="resend-btn"
                  disabled={isLoading}
                >
                  Resend Code
                </button>
                <button 
                  type="submit" 
                  className={`submit-btn ${isLoading ? 'loading' : ''}`}
                  disabled={isLoading}
                >
                  {isLoading ? 'Resetting...' : 'Reset Password'}
                </button>
              </div>
            </form>
          )}

          {/* Step 3: Success */}
          {step === 'success' && (
            <div className="success-content">
              <div className="success-icon">
                <CheckCircle size={48} />
              </div>
              <h3 className="success-title">Password Reset Successfully!</h3>
              <p className="success-description">
                Your password has been updated. You can now sign in with your new password.
              </p>
              <button 
                onClick={onClose}
                className="submit-btn"
              >
                Continue to Sign In
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordModal;