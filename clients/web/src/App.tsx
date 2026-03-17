/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Shield, 
  Zap, 
  BarChart3, 
  Network, 
  Github, 
  BookOpen, 
  ChevronRight, 
  Terminal,
  Lock,
  Mail,
  Search,
  LogOut,
  Cpu,
  CheckCircle2,
  X,
  ArrowLeft,
  Sun,
  Moon
} from 'lucide-react';

// --- Constants & API Config ---
const API_URL = (window as any).CODESAGE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "codesage_access_token";
const THEME_KEY = "codesage_theme";

// --- Types ---

interface Feature {
  title: string;
  description: string;
  icon: React.ReactNode;
}

type Page = 'landing' | 'login';

// --- Components ---

const Navbar = ({ onNavigate, currentPage, theme, onToggleTheme }: { 
  onNavigate: (page: Page) => void, 
  currentPage: Page,
  theme: 'light' | 'dark',
  onToggleTheme: () => void
}) => (
  <nav className="fixed top-0 left-0 right-0 z-50 px-8 py-6">
    <div className="max-w-7xl mx-auto flex items-center justify-between">
      <div 
        className="flex items-center gap-4 group cursor-pointer"
        onClick={() => onNavigate('landing')}
      >
        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center overflow-hidden border border-white/10 shadow-2xl">
          <img 
            src="" 
            alt="Logo" 
            className="w-full h-full object-cover"
            referrerPolicy="no-referrer"
          />
        </div>
        <span className="text-2xl font-display font-bold text-white tracking-tighter">CodeSage</span>
      </div>
      
      <div className="hidden md:flex items-center gap-10">
        {currentPage === 'landing' && (
          <>
            <a href="#features" className="nav-link">Features</a>
            <a href="#try" className="nav-link">Try</a>
            <a href="#docs" className="nav-link">Docs</a>
          </>
        )}
        <div className="flex items-center gap-4">
          <button 
            onClick={onToggleTheme}
            className="p-2.5 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all"
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
          <button 
            onClick={() => onNavigate('login')}
            className="btn-primary py-2.5 text-sm"
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  </nav>
);

const FeatureCard = ({ feature }: { feature: Feature; key?: React.Key }) => (
  <motion.div 
    className="p-10 rounded-[2.5rem] liquid-glass card-hover group"
  >
    <div className="w-14 h-14 rounded-2xl mb-8 flex items-center justify-center bg-white/5 text-white border border-white/10 group-hover:border-white/20 transition-colors">
      {feature.icon}
    </div>
    <h3 className="text-2xl mb-4 text-white">{feature.title}</h3>
    <p className="text-slate-500 leading-relaxed text-base">{feature.description}</p>
  </motion.div>
);

const LoginPage = ({ onBack, onLoginSuccess }: { onBack: () => void, onLoginSuccess: (token: string) => void, key?: React.Key }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMessage("Authenticating...");
    try {
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const payload = await res.json();

      if (!res.ok) {
        throw new Error(payload.detail || JSON.stringify(payload));
      }
      onLoginSuccess(payload.access_token);
    } catch (err: any) {
      setStatusMessage(`Authentication failed: ${err.message}`);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="min-h-screen flex items-center justify-center px-6"
    >
      <div className="w-full max-w-lg">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors mb-12 group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Back to platform
        </button>
        
        <div className="liquid-glass p-12 rounded-[3rem] border-white/5 shadow-2xl">
          <h2 className="text-4xl mb-2 metallic-text">Welcome back</h2>
          <p className="text-slate-500 mb-10">Enter your credentials to access the analysis engine.</p>
          
          <form onSubmit={handleLogin} className="space-y-8">
            <div className="space-y-3">
              <label className="block text-[10px] uppercase tracking-[0.3em] text-slate-500 font-bold ml-1">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-6 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-600" />
                <input 
                  type="email" 
                  className="input-field pl-16" 
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="space-y-3">
              <label className="block text-[10px] uppercase tracking-[0.3em] text-slate-500 font-bold ml-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-6 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-600" />
                <input 
                  type="password" 
                  className="input-field pl-16" 
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>
            <button type="submit" className="btn-primary w-full py-5 text-lg">Sign In</button>
            {statusMessage && (
              <p className="text-sm text-center text-slate-500 animate-pulse">{statusMessage}</p>
            )}
          </form>
        </div>
      </div>
    </motion.div>
  );
};

const LandingPage = ({ onNavigateToLogin, token, onLogout }: { onNavigateToLogin: () => void, token: string | null, onLogout: () => void, key?: React.Key }) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      onNavigateToLogin();
      return;
    }

    setIsAnalyzing(true);
    setAnalysisResult(null);
    setStatusMessage("Initializing analysis engine...");

    try {
      const authHeaders = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      };

      const createRepoRes = await fetch(`${API_URL}/api/v1/repositories`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({ url: repoUrl, branch }),
      });

      const createRepoPayload = await createRepoRes.json();

      if (!createRepoRes.ok) {
        setAnalysisResult(`Repository registration failed: ${JSON.stringify(createRepoPayload, null, 2)}`);
        setIsAnalyzing(false);
        return;
      }

      const analyzeRes = await fetch(`${API_URL}/api/v1/repositories/${createRepoPayload.id}/analyze`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({ analysis_types: ["security", "performance", "quality"] }),
      });

      const analyzePayload = await analyzeRes.json();

      if (!analyzeRes.ok) {
        setAnalysisResult(`Analysis request failed: ${JSON.stringify(analyzePayload, null, 2)}`);
        setIsAnalyzing(false);
        return;
      }

      setAnalysisResult(JSON.stringify({ repository: createRepoPayload, analysis: analyzePayload }, null, 2));
    } catch (error: any) {
      setAnalysisResult(`Network error: Unable to reach API at ${API_URL}`);
    } finally {
      setIsAnalyzing(false);
      setStatusMessage(null);
    }
  };

  const features: Feature[] = [
    {
      title: "Security Insights",
      description: "Detect vulnerabilities, secrets, and supply-chain risks automatically before they reach production.",
      icon: <Shield className="w-7 h-7 text-slate-300" />
    },
    {
      title: "Performance Profiling",
      description: "Point out bottlenecks and slow code paths. Optimize your application's runtime efficiency.",
      icon: <Zap className="w-7 h-7 text-slate-300" />
    },
    {
      title: "Code Quality Scoring",
      description: "Track maintainability, complexity, and style issues across your entire codebase with ease.",
      icon: <BarChart3 className="w-7 h-7 text-slate-300" />
    },
    {
      title: "Knowledge Graph",
      description: "Build a searchable model of your repo and dependency graph to understand complex relations.",
      icon: <Network className="w-7 h-7 text-slate-300" />
    }
  ];

  return (
    <div className="pt-32 pb-24">
      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-8 py-32">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          className="text-center max-w-5xl mx-auto"
        >
          <div className="inline-flex items-center gap-3 px-5 py-2 rounded-full bg-white/5 border border-white/10 text-slate-400 text-[11px] font-bold uppercase tracking-[0.4em] mb-12">
            <Cpu className="w-4 h-4" />
            Autonomous Analysis
          </div>
          
          <div className="mb-14">
            <div className="ide-screenshot">
              <div className="ide-header">
                <div className="ide-dot bg-[#ff5f56]" />
                <div className="ide-dot bg-[#ffbd2e]" />
                <div className="ide-dot bg-[#27c93f]" />
                <span className="ml-4 text-[10px] text-slate-500 font-mono">codesage.ts</span>
              </div>
              <div className="ide-content">
                <div className="text-3xl lg:text-5xl font-bold tracking-tight">
                  <span className="syntax-keyword">const</span> <span className="syntax-variable">CodeSage</span> = <span className="syntax-bracket">{"{"}</span> <br />
                  &nbsp;&nbsp;<span className="syntax-function">understandCode</span><span className="syntax-bracket">()</span> <span className="syntax-bracket">{"{"}</span> <br />
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="syntax-keyword">return</span> <span className="syntax-string">"with clarity."</span>; <br />
                  &nbsp;&nbsp;<span className="syntax-bracket">{"}"}</span> <br />
                  <span className="syntax-bracket">{"}"}</span>;
                </div>
              </div>
            </div>
          </div>

          <p className="text-xl text-slate-500 mb-14 leading-relaxed max-w-2xl mx-auto">
            CodeSage runs deep analysis across security, performance, and code quality — powered by AI and built for modern engineering teams.
          </p>
          <div className="flex flex-wrap justify-center gap-6">
            <a href="#try" className="btn-primary flex items-center gap-3">
              Get Started <ChevronRight className="w-5 h-5" />
            </a>
            <button 
              onClick={() => setShowModal(true)}
              className="btn-secondary"
            >
              Download Desktop
            </button>
          </div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section id="features" className="max-w-7xl mx-auto px-8 py-48">
        <div className="flex flex-col lg:flex-row items-baseline justify-between mb-24 gap-12">
          <div className="max-w-2xl">
            <h2 className="text-5xl lg:text-6xl mb-8 metallic-text">The core of CodeSage</h2>
            <p className="text-xl text-slate-500 leading-relaxed">
              Our multi-layered analysis engine looks beyond simple linting to provide deep architectural and security insights.
            </p>
          </div>
          <div className="text-slate-700 font-mono text-sm tracking-[0.3em] uppercase">
            Platform / Capabilities
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-8">
          {features.map((f, i) => (
            <FeatureCard key={i} feature={f} />
          ))}
        </div>
      </section>

      {/* Try Section */}
      <section id="try" className="max-w-7xl mx-auto px-8 py-48">
        <div className="liquid-glass rounded-[4rem] p-12 lg:p-24 relative overflow-hidden border-white/5">
          <div className="grid lg:grid-cols-2 gap-24 relative z-10">
            <div>
              <h2 className="text-5xl lg:text-6xl mb-10 metallic-text">Try it in seconds</h2>
              <p className="text-slate-500 mb-16 text-xl leading-relaxed">
                Connect your repository and instantly receive a comprehensive analysis report. No complex setup required.
              </p>
              
              <div className="space-y-12">
                <div className="flex items-start gap-6">
                  <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-white border border-white/10 flex-shrink-0 mt-1">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-xl text-white font-semibold mb-3">Instant Feedback</h4>
                    <p className="text-slate-500 leading-relaxed">Get results in under 60 seconds for most repositories.</p>
                  </div>
                </div>
                <div className="flex items-start gap-6">
                  <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-white border border-white/10 flex-shrink-0 mt-1">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-xl text-white font-semibold mb-3">Secure by Design</h4>
                    <p className="text-slate-500 leading-relaxed">Your code is analyzed in isolated environments and never stored.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-10">
              <div className="liquid-glass p-12 rounded-[3rem] border-white/5 shadow-2xl">
                <div className="flex items-center justify-between mb-10">
                  <h3 className="text-3xl metallic-text">Analyze Repo</h3>
                  {token && (
                    <button 
                      onClick={onLogout}
                      className="text-[10px] uppercase tracking-[0.3em] text-slate-600 hover:text-white flex items-center gap-2 transition-colors font-bold"
                    >
                      <LogOut className="w-4 h-4" /> Logout
                    </button>
                  )}
                </div>
                
                <form onSubmit={handleAnalyze} className="space-y-8">
                  <div className="space-y-3">
                    <label className="block text-[10px] uppercase tracking-[0.3em] text-slate-500 font-bold ml-1">Repository URL</label>
                    <div className="relative">
                      <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-600" />
                      <input 
                        type="url" 
                        className="input-field pl-16" 
                        placeholder="https://github.com/example/repo"
                        value={repoUrl}
                        onChange={(e) => setRepoUrl(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="space-y-3">
                    <label className="block text-[10px] uppercase tracking-[0.3em] text-slate-500 font-bold ml-1">Branch</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      required
                    />
                  </div>
                  <button 
                    type="submit" 
                    disabled={isAnalyzing}
                    className="btn-primary w-full py-5 flex items-center justify-center gap-4 disabled:opacity-50"
                  >
                    {isAnalyzing ? (
                      <>
                        <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                        Processing...
                      </>
                    ) : (
                      "Start Analysis"
                    )}
                  </button>
                  {statusMessage && (
                    <p className="text-sm text-center text-slate-500 animate-pulse">{statusMessage}</p>
                  )}
                </form>
              </div>

              {analysisResult && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="liquid-glass p-10 rounded-[3rem] border-white/10"
                >
                  <h4 className="text-[11px] font-bold text-white uppercase tracking-[0.4em] mb-8">Analysis Output</h4>
                  <pre className="text-xs font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap bg-black/40 p-6 rounded-2xl border border-white/5">
                    {analysisResult}
                  </pre>
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Docs Section */}
      <section id="docs" className="max-w-7xl mx-auto px-8 py-48">
        <div className="grid lg:grid-cols-2 gap-32 items-center">
          <div>
            <h2 className="text-5xl lg:text-6xl mb-10 metallic-text">Documentation</h2>
            <p className="text-slate-500 mb-16 text-xl leading-relaxed">
              Get started with the backend API, run the platform locally, and configure AI models for your specific needs.
            </p>
            <div className="grid sm:grid-cols-2 gap-6">
              {[
                { label: "Backend API", path: "services/api" },
                { label: "LLM Service", path: "services/llm" },
                { label: "Analysis Engine", path: "services/analysis" },
                { label: "Knowledge Graph", path: "services/knowledge" }
              ].map((doc, i) => (
                <div key={i} className="flex items-center gap-5 p-6 rounded-3xl bg-white/5 border border-white/5 hover:border-white/20 transition-all group">
                  <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-slate-400 group-hover:text-white transition-colors">
                    <BookOpen className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="text-white font-medium text-base mb-1">{doc.label}</div>
                    <code className="text-[11px] text-slate-600 font-mono">{doc.path}</code>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="hidden lg:block relative">
            <div className="relative liquid-glass rounded-[3rem] p-12 border-white/5 shadow-2xl">
              <div className="flex items-center gap-4 mb-10">
                <div className="w-2.5 h-2.5 rounded-full bg-white/30" />
                <span className="text-[11px] font-mono text-slate-600 uppercase tracking-[0.4em] font-bold">API Reference</span>
              </div>
              <div className="space-y-8 font-mono text-base">
                <div className="group cursor-pointer">
                  <div className="text-white/80 group-hover:text-white transition-colors">GET /api/v1/analysis/:id</div>
                  <div className="text-slate-600 text-xs mt-2"># Returns full analysis report object</div>
                </div>
                <div className="group cursor-pointer">
                  <div className="text-white/80 group-hover:text-white transition-colors">POST /api/v1/analyze</div>
                  <div className="text-slate-600 text-xs mt-2"># Triggers new asynchronous repo scan</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-8 pt-48 pb-16 border-t border-white/5">
        <div className="flex flex-col md:flex-row justify-between items-center gap-16">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
              <img src="" alt="Logo" className="w-full h-full object-cover" />
            </div>
            <span className="text-2xl font-display font-bold text-white tracking-tighter">CodeSage</span>
          </div>
          
          <div className="flex items-center gap-12 text-[11px] uppercase tracking-[0.4em] font-bold text-slate-600">
            <a href="#" className="hover:text-white transition-colors flex items-center gap-2">
              <Github className="w-5 h-5" /> GitHub
            </a>
            <a href="#" className="hover:text-white transition-colors">Docs</a>
            <a href="#" className="hover:text-white transition-colors">License</a>
          </div>
          
          <div className="text-[11px] uppercase tracking-[0.4em] font-bold text-slate-800">
            &copy; 2026 CodeSage AI.
          </div>
        </div>
      </footer>

      {/* Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-8">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowModal(false)}
              className="absolute inset-0 bg-black/95 backdrop-blur-xl" 
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 40 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 40 }}
              className="relative w-full max-w-lg liquid-glass rounded-[4rem] p-16 border-white/10 shadow-2xl"
            >
              <button 
                onClick={() => setShowModal(false)}
                className="absolute top-10 right-10 text-slate-600 hover:text-white transition-colors"
              >
                <X className="w-8 h-8" />
              </button>
              <div className="w-24 h-24 rounded-[2.5rem] bg-white/5 flex items-center justify-center text-white mb-10 border border-white/10">
                <Cpu className="w-12 h-12" />
              </div>
              <h2 className="text-5xl mb-8 metallic-text">Coming Soon</h2>
              <p className="text-slate-500 mb-12 text-lg leading-relaxed">
                Our native desktop applications for macOS, Windows, and Linux are currently in private beta. Join the waitlist to get early access.
              </p>
              <div className="space-y-5">
                <button className="btn-primary w-full py-5 text-lg">Join Waitlist</button>
                <button 
                  onClick={() => setShowModal(false)}
                  className="btn-secondary w-full py-5 text-lg"
                >
                  Maybe Later
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('landing');
  const [token, setToken] = useState<string | null>(localStorage.getItem(TOKEN_KEY));
  const [theme, setTheme] = useState<'light' | 'dark'>((localStorage.getItem(THEME_KEY) as 'light' | 'dark') || 'dark');

  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }, [token]);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
    if (theme === 'light') {
      document.body.classList.add('light');
    } else {
      document.body.classList.remove('light');
    }
  }, [theme]);

  const handleLoginSuccess = (newToken: string) => {
    setToken(newToken);
    setCurrentPage('landing');
  };

  const handleLogout = () => {
    setToken(null);
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <div className="min-h-screen text-slate-400">
      <div className="app-background" />
      <div className="app-overlay" />
      
      <Navbar 
        onNavigate={setCurrentPage} 
        currentPage={currentPage} 
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <AnimatePresence mode="wait">
        {currentPage === 'landing' ? (
          <LandingPage 
            key="landing"
            onNavigateToLogin={() => setCurrentPage('login')} 
            token={token}
            onLogout={handleLogout}
          />
        ) : (
          <LoginPage 
            key="login"
            onBack={() => setCurrentPage('landing')}
            onLoginSuccess={handleLoginSuccess}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
