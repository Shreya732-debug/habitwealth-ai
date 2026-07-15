import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '../api';

export default function Login() {
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [mode,     setMode]     = useState<'login'|'signup'>('login');
  const [error,    setError]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setError(''); setLoading(true);
    try {
      if (mode === 'signup') {
        await API.post('/auth/signup', { email, password });
      }
      const res = await API.post('/auth/login', { email, password });
      localStorage.setItem('access_token', res.data.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Something went wrong');
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-cream flex items-center justify-center p-4">
      <div className="bg-white border border-cardBorder rounded-2xl p-8 w-full max-w-sm shadow-sm">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-coral rounded-xl flex items-center justify-center text-2xl mx-auto mb-3">💰</div>
          <h1 className="text-xl font-medium text-gray-900">FinanceGPT</h1>
          <p className="text-muted text-sm mt-1">Your AI budget assistant</p>
        </div>

        <div className="flex bg-cream rounded-lg p-1 mb-5">
          {(['login','signup'] as const).map(m => (
            <button key={m} onClick={() => setMode(m)}
              className={`flex-1 py-2 rounded-md text-sm font-medium transition-all capitalize ${
                mode === m ? 'bg-coral text-white' : 'text-muted hover:text-gray-900'
              }`}>
              {m === 'login' ? 'Log in' : 'Sign up'}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          <input type="email" placeholder="Email" value={email}
            onChange={e => setEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            className="w-full border border-cardBorder rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-coral transition-colors bg-cream" />
          <input type="password" placeholder="Password" value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            className="w-full border border-cardBorder rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-coral transition-colors bg-cream" />
        </div>

        {error && <p className="mt-3 text-red-500 text-xs bg-red-50 p-3 rounded-lg">{error}</p>}

        <button onClick={handleSubmit} disabled={loading || !email || !password}
          className="w-full mt-5 bg-coral hover:bg-coral/90 disabled:bg-gray-200 disabled:text-gray-400 text-white font-medium py-3 rounded-lg transition-all text-sm">
          {loading ? 'Please wait...' : mode === 'login' ? 'Log in' : 'Create account'}
        </button>
      </div>
    </div>
  );
}