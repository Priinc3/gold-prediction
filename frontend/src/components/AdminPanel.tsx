import { API_BASE_URL } from '../config';
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Save, Shield, Key, Database, CheckCircle2, AlertCircle, Loader2, Lock, Unlock, Eye, EyeOff } from 'lucide-react';
import TrainingDataForm from './TrainingDataForm';

interface SystemSettingsState {
  default_llm: string;
  gemini_model: string;
  anthropic_api_key: string;
  gemini_api_key: string;
  pinecone_api_key: string;
  pinecone_index_name: string;
  pinecone_index_host: string;
  has_anthropic: boolean;
  has_gemini: boolean;
  has_pinecone: boolean;
  is_authorized: boolean;
}

const GEMINI_MODELS = [
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash (Recommended - Fastest & Multi-modal)' },
  { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash (Low Latency)' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro (Deep Visual Reasoning)' },
  { value: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash Lite (Next-Gen Preview)' },
  { value: 'gemini-3.5-flash', label: 'Gemini 3.5 Flash (Experimental)' }
];

const AdminPanel: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettingsState>({
    default_llm: 'gemini',
    gemini_model: 'gemini-2.5-flash',
    anthropic_api_key: '',
    gemini_api_key: '',
    pinecone_api_key: '',
    pinecone_index_name: '',
    pinecone_index_host: '',
    has_anthropic: false,
    has_gemini: false,
    has_pinecone: false,
    is_authorized: false
  });
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [passwordInput, setPasswordInput] = useState('');
  const [showKeys, setShowKeys] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  // Instant Unlock Trigger: Whenever password input equals "774623", trigger a settings fetch!
  useEffect(() => {
    fetchSettings(passwordInput);
  }, [passwordInput]);

  const fetchSettings = async (pwd: string = '') => {
    try {
      const response = await axios.get(API_BASE_URL + '/settings', {
        params: pwd ? { password: pwd } : {}
      });
      setSettings(response.data);
      if (response.data.is_authorized) {
        setMessage(null);
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err);
      // Don't show loading errors for incorrect live password typings
      if (!pwd) {
        setMessage({ type: 'error', text: 'Failed to load settings.' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordInput !== '774623') {
      setMessage({ type: 'error', text: 'Authorization Required: Please enter the correct admin password (774623) to apply changes.' });
      return;
    }

    setSaving(true);
    setMessage(null);
    
    try {
      await axios.post(API_BASE_URL + '/settings', {
        default_llm: settings.default_llm,
        gemini_model: settings.gemini_model,
        anthropic_api_key: settings.anthropic_api_key,
        gemini_api_key: settings.gemini_api_key,
        pinecone_api_key: settings.pinecone_api_key,
        pinecone_index_name: settings.pinecone_index_name,
        pinecone_index_host: settings.pinecone_index_host,
        password: passwordInput
      });
      setMessage({ type: 'success', text: 'System settings successfully updated on server and Vector DB namespaces!' });
      fetchSettings(passwordInput);
    } catch (err: any) {
      console.error('Failed to update settings:', err);
      const detail = err.response?.data?.detail || 'Failed to update settings. Verify credentials and try again.';
      setMessage({ type: 'error', text: detail });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
      </div>
    );
  }

  const isUnlocked = settings.is_authorized;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Admin Panel Welcome Banner */}
      <div className="bg-blue-50 border border-blue-100 rounded-2xl p-6 mb-8 flex items-start">
        <Shield className="h-6 w-6 text-blue-600 mr-4 mt-0.5 flex-shrink-0" />
        <div className="text-sm text-blue-800">
          <p className="font-bold text-base">Administrator Access Control</p>
          <p className="mt-1 leading-relaxed text-blue-700">
            Manage LLM model aliases, secure API credentials, and Pinecone vector indexing pools. A password is required to reveal or write configurations.
          </p>
        </div>
      </div>

      {/* PASSWORD GATE */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-8 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {isUnlocked ? (
              <Unlock className="h-5 w-5 text-green-600 animate-pulse" />
            ) : (
              <Lock className="h-5 w-5 text-red-500" />
            )}
            <h3 className="font-bold text-gray-800">System Lock Status</h3>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
            isUnlocked ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
          }`}>
            {isUnlocked ? 'UNLOCKED / AUTHORIZED' : 'LOCKED / READ-ONLY'}
          </span>
        </div>
        
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Admin Authorization Password</label>
          <input
            type="password"
            value={passwordInput}
            onChange={(e) => setPasswordInput(e.target.value)}
            placeholder="Type password (774623) to edit credentials..."
            className={`w-full p-3.5 border rounded-xl outline-none focus:ring-2 focus:ring-accent transition-all text-sm font-bold tracking-widest ${
              isUnlocked ? 'border-green-300 bg-green-50/10 focus:ring-green-400' : 'border-gray-200 focus:border-red-400'
            }`}
          />
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8 mb-12">
        {/* Model Provider Options */}
        <div className={isUnlocked ? 'opacity-100 transition-opacity' : 'opacity-60 pointer-events-none'}>
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center">
            <Database className="h-4 w-4 mr-2 text-accent" />
            Active LLM Model Selection
          </h3>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <label className={`relative flex flex-col p-4 border-2 rounded-xl cursor-pointer transition-all ${
              settings.default_llm === 'gemini' ? 'border-accent bg-blue-50/30' : 'border-gray-200 hover:border-gray-300'
            }`}>
              <input 
                type="radio" name="default_llm" value="gemini" 
                checked={settings.default_llm === 'gemini'} 
                onChange={() => setSettings({...settings, default_llm: 'gemini'})}
                className="sr-only" 
                disabled={!isUnlocked}
              />
              <span className="font-bold text-[#111827]">Google Gemini Studio</span>
              <span className="text-xs text-gray-500 mt-1">Multi-modal & Incredibly Fast</span>
              {settings.has_gemini && (
                <span className="absolute top-4 right-4 text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                </span>
              )}
            </label>
            <label className={`relative flex flex-col p-4 border-2 rounded-xl cursor-pointer transition-all ${
              settings.default_llm === 'anthropic' ? 'border-accent bg-blue-50/30' : 'border-gray-200 hover:border-gray-300'
            }`}>
              <input 
                type="radio" name="default_llm" value="anthropic" 
                checked={settings.default_llm === 'anthropic'} 
                onChange={() => setSettings({...settings, default_llm: 'anthropic'})}
                className="sr-only" 
                disabled={!isUnlocked}
              />
              <span className="font-bold text-[#111827]">Anthropic Claude</span>
              <span className="text-xs text-gray-500 mt-1">Sonnet 3.5 Precision Reasoning</span>
              {settings.has_anthropic && (
                <span className="absolute top-4 right-4 text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                </span>
              )}
            </label>
          </div>

          {/* Model Alias Dropdown */}
          {settings.default_llm === 'gemini' && (
            <div className="bg-gray-50 p-4 border border-gray-150 rounded-2xl">
              <label className="block text-xs font-bold text-gray-600 uppercase mb-2">Gemini Model Model ID</label>
              <select
                value={settings.gemini_model}
                onChange={(e) => setSettings({...settings, gemini_model: e.target.value})}
                disabled={!isUnlocked}
                className="w-full p-3 bg-white border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-accent font-medium text-sm text-gray-700 cursor-pointer"
              >
                {GEMINI_MODELS.map(model => (
                  <option key={model.value} value={model.value}>{model.label}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* API Credentials Card */}
        <div className={isUnlocked ? 'opacity-100 transition-opacity' : 'opacity-60 pointer-events-none'}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center">
              <Key className="h-4 w-4 mr-2 text-accent" />
              API & Cloud Credentials
            </h3>
            {isUnlocked && (
              <button
                type="button"
                onClick={() => setShowKeys(!showKeys)}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-accent font-semibold"
              >
                {showKeys ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                {showKeys ? 'Mask Keys' : 'Reveal Keys'}
              </button>
            )}
          </div>
          
          <div className="space-y-4 bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Google Gemini API Key</label>
              <input
                type={showKeys && isUnlocked ? "text" : "password"}
                value={settings.gemini_api_key}
                onChange={(e) => setSettings({...settings, gemini_api_key: e.target.value})}
                disabled={!isUnlocked}
                placeholder={settings.has_gemini && !isUnlocked ? "••••••••••••••••" : "Enter Google AI Studio Gemini API Key"}
                className="w-full p-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent outline-none transition-all text-sm font-mono"
              />
            </div>
            
            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Anthropic API Key</label>
              <input
                type={showKeys && isUnlocked ? "text" : "password"}
                value={settings.anthropic_api_key}
                onChange={(e) => setSettings({...settings, anthropic_api_key: e.target.value})}
                disabled={!isUnlocked}
                placeholder={settings.has_anthropic && !isUnlocked ? "••••••••••••••••" : "Enter Anthropic Console Claude API Key"}
                className="w-full p-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent outline-none transition-all text-sm font-mono"
              />
            </div>

            <hr className="border-gray-100 my-4" />
            
            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Pinecone API Key</label>
              <input
                type={showKeys && isUnlocked ? "text" : "password"}
                value={settings.pinecone_api_key}
                onChange={(e) => setSettings({...settings, pinecone_api_key: e.target.value})}
                disabled={!isUnlocked}
                placeholder={settings.has_pinecone && !isUnlocked ? "••••••••••••••••" : "Enter Pinecone Vector API Key"}
                className="w-full p-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent outline-none transition-all text-sm font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Pinecone Index Name</label>
                <input
                  type="text"
                  value={settings.pinecone_index_name}
                  onChange={(e) => setSettings({...settings, pinecone_index_name: e.target.value})}
                  disabled={!isUnlocked}
                  placeholder="e.g. ring-designs-v3"
                  className="w-full p-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent outline-none transition-all text-sm"
                />
              </div>
              
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Pinecone Index Host</label>
                <input
                  type="text"
                  value={settings.pinecone_index_host}
                  onChange={(e) => setSettings({...settings, pinecone_index_host: e.target.value})}
                  disabled={!isUnlocked}
                  placeholder="e.g. https://index-host.svc.pinecone.io"
                  className="w-full p-3 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent outline-none transition-all text-sm font-mono text-xs"
                />
              </div>
            </div>
          </div>
        </div>

        {message && (
          <div className={`p-4 rounded-xl flex items-center text-sm ${
            message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-100 animate-fadeIn' : 'bg-red-50 text-red-700 border border-red-100 animate-fadeIn'
          }`}>
            {message.type === 'success' ? <CheckCircle2 className="h-5 w-5 mr-3 flex-shrink-0" /> : <AlertCircle className="h-5 w-5 mr-3 flex-shrink-0" />}
            <span className="font-semibold">{message.text}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={saving || !isUnlocked}
          className="w-full bg-[#111827] text-white py-4 rounded-xl font-bold hover:bg-gray-800 transition-all transform hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-gray-200"
        >
          {saving ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Saving Settings...
            </>
          ) : (
            <>
              <Save className="h-5 w-5 mr-2" />
              Apply Credentials & Models
            </>
          )}
        </button>
      </form>

      <hr className="border-gray-100 my-12" />

      {/* Render Ingestion form at bottom */}
      <TrainingDataForm />
    </div>
  );
};

export default AdminPanel;
