import React, { useState, useEffect, useRef } from 'react';
import { Mail, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import '../styles/EmailVerification.css';

const EmailVerification = ({ email, onVerificationSuccess, onBackToSignup }) => {
  const [verificationCode, setVerificationCode] = useState(['', '', '', '', '', '']);
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [errors, setErrors] = useState({});
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendCount, setResendCount] = useState(0);
  
  // Refs for input fields
  const inputRefs = useRef([]);

  // Cooldown timer
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleInputChange = (index, value) => {
    if (value.length > 1) return; // Only allow single digit
    if (value && !/^\d$/.test(value)) return; // Only allow digits

    const newCode = [...verificationCode];
    newCode[index] = value;
    setVerificationCode(newCode);
    setErrors({});

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !verificationCode[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const paste = e.clipboardData.getData('text');
    const digits = paste.replace(/\D/g, '').slice(0, 6);
    
    const newCode = Array(6).fill('');
    for (let i = 0; i < digits.length; i++) {
      newCode[i] = digits[i];
    }
    setVerificationCode(newCode);
    
    // Focus the next empty field or the last field
    const nextEmpty = newCode.findIndex(digit => digit === '');
    const focusIndex = nextEmpty === -1 ? 5 : nextEmpty;
    inputRefs.current[focusIndex]?.focus();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const code = verificationCode.join('');
    if (code.length !== 6) {
      setErrors({ code: 'Please enter the complete 6-digit code' });
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/verify-email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          verification_code: code
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store the token and user info
        localStorage.setItem('authToken', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        onVerificationSuccess?.(data.user, data.access_token);
      } else {
        setErrors({ submit: data.detail || 'Verification failed. Please try again.' });
        setVerificationCode(['', '', '', '', '', '']);
        inputRefs.current[0]?.focus();
      }
    } catch (error) {
      console.error('Verification error:', error);
      setErrors({ submit: 'Network error. Please try again.' });
      setVerificationCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (resendCooldown > 0 || resendCount >= 3) return;

    setIsResending(true);
    setErrors({});

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        if (data.already_verified) {
          setErrors({ info: 'Email is already verified. You can log in directly.' });
        } else {
          setResendCount(prev => prev + 1);
          setResendCooldown(60); // 60 second cooldown
          setErrors({ info: 'Verification code sent! Check your email.' });
          setVerificationCode(['', '', '', '', '', '']);
          inputRefs.current[0]?.focus();
        }
      } else {
        setErrors({ submit: data.detail || 'Failed to resend code. Please try again.' });
      }
    } catch (error) {
      console.error('Resend error:', error);
      setErrors({ submit: 'Network error. Please try again.' });
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="email-verification-page">
      <div className="verification-container">
        {/* Header */}
        <div className="verification-header">
          <div className="logo-container">
            <Mail className="logo-icon" />
          </div>
          <h1 className="verification-title">Verify Your Email</h1>
          <p className="verification-subtitle">
            We've sent a 6-digit verification code to
          </p>
          <p className="email-display">{email}</p>
        </div>

        {/* Verification Form */}
        <div className="verification-form-container">
          <form onSubmit={handleSubmit} className="verification-form">
            
            {/* Code Input */}
            <div className="code-input-container">
              <label className="code-label">Enter verification code</label>
              <div className="code-inputs">
                {verificationCode.map((digit, index) => (
                  <input
                    key={index}
                    ref={el => inputRefs.current[index] = el}
                    type="text"
                    inputMode="numeric"
                    maxLength="1"
                    value={digit}
                    onChange={(e) => handleInputChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    onPaste={handlePaste}
                    className={`code-input ${errors.code || errors.submit ? 'error' : ''}`}
                    disabled={isLoading}
                    autoComplete="one-time-code"
                  />
                ))}
              </div>
              {errors.code && (
                <span className="error-message">{errors.code}</span>
              )}
            </div>

            {/* Submit Button */}
            <button 
              type="submit" 
              className="verify-button"
              disabled={isLoading || verificationCode.join('').length !== 6}
            >
              {isLoading ? (
                <>
                  <RefreshCw className="spinner" />
                  Verifying...
                </>
              ) : (
                <>
                  <CheckCircle className="button-icon" />
                  Verify Email
                </>
              )}
            </button>

            {/* Error Messages */}
            {errors.submit && (
              <div className="error-message-box">
                <AlertCircle className="error-icon" />
                {errors.submit}
              </div>
            )}

            {/* Info Messages */}
            {errors.info && (
              <div className="info-message-box">
                <CheckCircle className="info-icon" />
                {errors.info}
              </div>
            )}

          </form>

          {/* Resend Section */}
          <div className="resend-section">
            <p className="resend-text">Didn't receive the code?</p>
            <div className="resend-actions">
              <button
                type="button"
                onClick={handleResendCode}
                className="resend-button"
                disabled={isResending || resendCooldown > 0 || resendCount >= 3}
              >
                {isResending ? (
                  <>
                    <RefreshCw className="spinner" />
                    Sending...
                  </>
                ) : resendCooldown > 0 ? (
                  `Resend in ${resendCooldown}s`
                ) : resendCount >= 3 ? (
                  'Maximum attempts reached'
                ) : (
                  <>
                    <RefreshCw className="resend-icon" />
                    Resend Code
                  </>
                )}
              </button>
              
              <button
                type="button"
                onClick={onBackToSignup}
                className="back-button"
              >
                Back to Signup
              </button>
            </div>
          </div>

          {/* Tips */}
          <div className="verification-tips">
            <h3>Tips:</h3>
            <ul>
              <li>Check your spam/junk folder if you don't see the email</li>
              <li>The code expires in 30 minutes</li>
              <li>Make sure you entered the correct email address</li>
              <li>You can resend the code up to 3 times</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailVerification;