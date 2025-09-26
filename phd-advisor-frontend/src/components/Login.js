import React, { useState } from 'react';
import { Eye, EyeOff, Mail, Lock, ArrowRight, BookOpen, Phone } from 'lucide-react';
import ForgotPasswordModal from './ForgotPasswordModal';
import '../styles/Login.css';

const Login = ({ onNavigateToSignup, onNavigateToHome, onNavigateToVerification }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [showForgotPasswordModal, setShowForgotPasswordModal] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsLoading(true);
    
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store the token and user info
        localStorage.setItem('authToken', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        onNavigateToHome?.(data.user, data.access_token);
      } else {
        // Check if it's an email verification error
        if (response.status === 403 && data.detail.includes('Email not verified')) {
          setErrors({ 
            verification: 'Please verify your email address to continue.',
            showVerificationButton: true 
          });
        } else {
          setErrors({ submit: data.detail || 'Login failed. Please try again.' });
        }
      }
      
    } catch (error) {
      console.error('Login error:', error);
      setErrors({ submit: 'Login failed. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = () => {
    setShowForgotPasswordModal(true);
  };

  const handleGoogleSignIn = () => {
    console.log('Google Sign In clicked');
    // Future Google Auth integration will go here
  };

  const handlePhoneSignIn = () => {
    console.log('Phone Sign In clicked');
    // Future Phone Auth integration will go here
  };

  return (
    <div className="login-page">
      <div className="login-container">
        {/* Header */}
        <div className="login-header">
          <div className="logo-container">
            <BookOpen className="logo-icon" />
          </div>
          <h1 className="login-title">Welcome Back</h1>
          <p className="login-subtitle">
            Sign in to continue your PhD research journey
          </p>
        </div>

        {/* Main Login Form */}
        <div className="login-form-container">
          <form onSubmit={handleSubmit} className="login-form">
            
            {/* Email Field */}
            <div className="form-group">
              <label htmlFor="email" className="form-label">
                Email Address
              </label>
              <div className="input-container">
                <Mail className="input-icon" />
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className={`form-input ${errors.email ? 'error' : ''}`}
                  placeholder="Enter your email"
                  disabled={isLoading}
                />
              </div>
              {errors.email && (
                <span className="error-message">{errors.email}</span>
              )}
            </div>

            {/* Password Field */}
            <div className="form-group">
              <label htmlFor="password" className="form-label">
                Password
              </label>
              <div className="input-container">
                <Lock className="input-icon" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  className={`form-input ${errors.password ? 'error' : ''}`}
                  placeholder="Enter your password"
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
              {errors.password && (
                <span className="error-message">{errors.password}</span>
              )}
              {errors.verification && (
                <div className="verification-notice" style={{
                  background: '#fef3cd',
                  border: '1px solid #fcd34d',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px'
                }}>
                  <div style={{ color: '#d97706' }}>⚠️</div>
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: '0 0 8px 0', color: '#92400e', fontSize: '14px' }}>
                      {errors.verification}
                    </p>
                    {errors.showVerificationButton && (
                      <button
                        type="button"
                        onClick={() => onNavigateToVerification?.(formData.email)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#d97706',
                          fontSize: '14px',
                          fontWeight: '600',
                          textDecoration: 'underline',
                          cursor: 'pointer',
                          padding: '0'
                        }}
                      >
                        Verify Email Now
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
            

            {/* Forgot Password */}
            <div className="form-actions">
              <button 
                type="button" 
                className="forgot-password"
                onClick={handleForgotPassword}
                disabled={isLoading}
              >
                Forgot your password?
              </button>
            </div>

            {/* Submit Error */}
            {errors.submit && (
              <div className="submit-error">
                {errors.submit}
              </div>
            )}

            {/* Submit Button */}
            <button 
              type="submit" 
              className={`submit-btn ${isLoading ? 'loading' : ''}`}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <div className="loading-spinner"></div>
                  Signing In...
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight size={16} />
                </>
              )}
            </button>

          </form>

          {/* Divider */}
          <div className="login-divider">
            <span className="divider-text">or continue with</span>
          </div>

          {/* Alternative Sign In Methods */}
          <div className="alt-signin-container">
            <button 
              onClick={handleGoogleSignIn}
              className="google-btn"
              disabled={isLoading}
            >
              <svg width="16" height="16" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google
            </button>
            
            <button 
              onClick={handlePhoneSignIn}
              className="phone-btn"
              disabled={isLoading}
            >
              <Phone size={16} />
              Phone
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="login-footer">
          <p className="footer-text">
            Don't have an account?{' '}
            <button 
              onClick={onNavigateToSignup}
              className="link-btn"
              disabled={isLoading}
            >
              Sign up here
            </button>
          </p>
        </div>
      </div>

      {/* Forgot Password Modal */}
      <ForgotPasswordModal 
        isOpen={showForgotPasswordModal}
        onClose={() => setShowForgotPasswordModal(false)}
      />
    </div>
  );
};

export default Login;