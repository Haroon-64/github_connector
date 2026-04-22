import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    axios.get('/auth/me')
      .then(() => {
        navigate('/dashboard');
      })
      .catch(() => {
        setLoading(false);
      });
  }, [navigate]);
  return (
    <div className="flex-center min-h-screen" style={{ marginTop: '-70px' }}>
      <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', maxWidth: '400px', width: '100%' }}>
        <h1 style={{ marginBottom: '16px', fontSize: '2rem' }}>Welcome Back</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', lineHeight: '1.6' }}>
          Sign in to access your GitHub PR review dashboard and orchestrate workflows with Camunda.
        </p>
        
        {loading ? (
          <div style={{ color: 'var(--text-secondary)' }}>Checking session...</div>
        ) : (
          <a href="http://127.0.0.1:8000/auth/github/login" className="btn-primary" style={{ width: '100%' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
              <path d="M9 18c-4.51 2-5-2-7-2" />
            </svg>
            Continue with GitHub
          </a>
        )}
      </div>
    </div>
  );
}