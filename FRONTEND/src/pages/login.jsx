import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [errorMessage, setErrorMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    const trimmedUsername = formData.username.trim();
    if (!trimmedUsername || !formData.password) {
      setErrorMessage('Please enter both your User ID and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(trimmedUsername, formData.password);
      navigate('/dashboard');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setErrorMessage(detail || 'Login failed. Check your credentials and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col md:flex-row bg-slate-50 font-sans overflow-hidden">

      {/* LEFT SECTION: BRANDING & SYSTEM FEATURES */}
      <div className="w-full md:w-1/2 md:h-screen overflow-hidden bg-slate-900 text-white p-6 lg:p-8 xl:p-10 flex flex-col justify-between relative">

        <div className="absolute -top-24 -left-24 w-80 h-80 bg-emerald-500/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-80 h-80 bg-blue-600/20 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 mb-4">
          <div className="flex items-center gap-2.5">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              className="w-7 h-7 text-emerald-400 shrink-0"
            >
              {/* Shield */}
              <path
                d="M12 2.5L20 5.8V11.5C20 16.5 16.8 20.2 12 21.5C7.2 20.2 4 16.5 4 11.5V5.8L12 2.5Z"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Network / traffic signal */}
              <path
                d="M7.5 12.5L10 10L12 13L15 9.5L17 11.5"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Network nodes */}
              <circle cx="7.5" cy="12.5" r="1" fill="currentColor" />
              <circle cx="10" cy="10" r="1" fill="currentColor" />
              <circle cx="12" cy="13" r="1" fill="currentColor" />
              <circle cx="15" cy="9.5" r="1" fill="currentColor" />
              <circle cx="17" cy="11.5" r="1" fill="currentColor" />
            </svg>
            <span className="text-2xl font-black tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 leading-none block">
              SOPHOSMIXX
            </span>
          </div>
          <p className="text-[11px] text-slate-400 uppercase tracking-widest font-semibold mt-1">
            ANOMALY DETECTION SYSTEM
          </p>
        </div>

        <div className="relative z-10 my-auto py-2">
          <div className="inline-block px-3 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px] font-semibold uppercase tracking-wider mb-3">
            AI DRIVEN NETWORK TRAFFIC ANOMALY DETECTION
          </div>

          <h1 className="text-2xl lg:text-3xl xl:text-4xl font-extrabold leading-tight text-white mb-3">
            AI-Driven Detection. <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-amber-400 via-emerald-400 to-teal-300">
              Adaptive Security.
            </span> <br />
            Stronger Networks Security.
          </h1>

          <p className="text-slate-300 text-xs lg:text-sm max-w-lg mb-5 leading-relaxed">
            Welcome to SOPHOSMIXX. Detect network traffic anomalies and gain intelligent insights for stronger network security.
          </p>

          <div className="grid grid-cols-2 gap-3 max-w-lg">
            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/50 backdrop-blur-sm hover:border-emerald-500/50 transition-colors">
              <h4 className="text-sm font-bold text-slate-100">Intelligent Anomaly Detection</h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-normal">
                Detect unusual patterns in network traffic.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/50 backdrop-blur-sm hover:border-blue-500/50 transition-colors">
              <h4 className="text-sm font-bold text-slate-100">AI-Powered Security Insights</h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-normal">
                Understand anomalies through clear, actionable explanations.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/50 backdrop-blur-sm hover:border-amber-500/50 transition-colors">
              <h4 className="text-sm font-bold text-slate-100">Sophos Log Analysis</h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-normal">
                Analyze uploaded firewall logs efficiently and consistently.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/50 backdrop-blur-sm hover:border-purple-500/50 transition-colors">
              <h4 className="text-sm font-bold text-slate-100">Security Monitoring Dashboard</h4>
              <p className="text-[11px] text-slate-300 mt-1 leading-normal">
                Track network activity, anomalies, and security trends in one place.
              </p>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-[11px] text-slate-400 border-t border-slate-800/80 pt-2.5 mt-4">
          <span>SOPHOSMIXX Anomaly Detection System</span>
        </div>
      </div>

      {/* RIGHT SECTION: LOGIN FORM */}
      <div className="w-full md:w-1/2 md:h-screen overflow-hidden flex items-center justify-center p-6 lg:p-10 bg-white">
        <div className="w-full max-w-sm space-y-4 py-6">

          <div>
            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 mb-2">
              ⚡ welcome back Network Engineer
            </span>

            <h2 className="text-2xl lg:text-3xl font-extrabold text-slate-900 tracking-tight">
              Network Engineer Sign In
            </h2>

            <p className="text-slate-600 text-xs mt-1">
              Enter your credentials to access the dashboard.
            </p>
          </div>

          {errorMessage && (
            <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
              {errorMessage}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5" autoComplete="off">

            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                USER ID
              </label>

              <input
                type="text"
                required
                maxLength={50}
                autoComplete="off"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="Enter your User ID"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-xs font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-sm"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                PASSWORD
              </label>

              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  maxLength={64}
                  autoComplete="current-password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 pr-10 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-xs font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-sm"
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors focus:outline-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-4 h-4"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
                      />
                    </svg>
                  ) : (
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="w-4 h-4"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M2.036 12c1.274 4.057 5.065 7 9.542 7 4.477 0 8.268-2.943 9.542-7-1.274-4.057-5.065-7-9.542-7-4.477 0-8.268 2.943-9.542 7z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={`w-full text-white font-semibold py-2.5 px-4 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 group shadow-lg text-xs mt-1 ${
                isSubmitting
                  ? 'bg-slate-400 cursor-not-allowed shadow-none'
                  : 'bg-slate-900 hover:bg-slate-800 shadow-slate-900/10 active:scale-[0.99]'
              }`}
            >
              <span>
                {isSubmitting ? 'Signing in...' : 'Sign In to Dashboard →'}
              </span>
            </button>
          </form>

          {/* Imeongezwa nafasi zaidi (mt-6) na ukubwa wa maandishi umekuzwa (text-xs) */}
          <div className="pt-4 mt-6 text-center space-y-2 border-t border-slate-100">
            <p className="text-xs text-slate-600 font-medium">
              Having trouble signing in? Contact Data Scientists.
            </p>

            <p className="text-xs text-slate-500 font-medium">
              © 2026 SOPHOSMIXX — AI-Driven Network Traffic Anomaly Detection
            </p>
          </div>

        </div>
      </div>
    </div>
  );
}